import base64

from skimage.feature import match_template
import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
import os
import random
import tempfile
from openai import OpenAI
from Config import is_method_enabled


class MultiImagesMethod:
    def __init__(self):
        self.method_parameters = {'cmd_block_size': 64}
        self.cache_path_root = ''
        pass

    def set_cache_path_root(self, cache_path_root):
        self.cache_path_root = cache_path_root

    def get_methods(self):
        return [
            method
            for name, method in self.get_method_map()
            if is_method_enabled('multi_images', name)
        ]

    def get_methods_name(self):
        return [
            name
            for name, _ in self.get_method_map()
            if is_method_enabled('multi_images', name)
        ]

    def get_method_map(self):
        return [
            ('llm', self.llm_method),
            ('ela', self.ela_method),
            ('exif', self.exif_method),
            ('cmd', self.cmd_method),
        ]

    def cmd_method(self, image_path):
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        matches = []

        for y in range(0, h - self.method_parameters['cmd_block_size'], self.method_parameters['cmd_block_size'] // 2):
            for x in range(0, w - self.method_parameters['cmd_block_size'],
                           self.method_parameters['cmd_block_size'] // 2):
                block = gray[y:y + self.method_parameters['cmd_block_size'],
                        x:x + self.method_parameters['cmd_block_size']]
                result = match_template(gray, block)
                loc = np.where(result >= 0.9)
                for pt in zip(*loc[::-1]):
                    if abs(pt[0] - x) > self.method_parameters['cmd_block_size'] or abs(pt[1] - y) > \
                            self.method_parameters['cmd_block_size']:
                        matches.append((x, y, pt[0], pt[1]))

        # build mask
        mask = np.zeros_like(gray)
        for x1, y1, x2, y2 in matches:
            mask[y1:y1 + self.method_parameters['cmd_block_size'],
            x1:x1 + self.method_parameters['cmd_block_size']] = 255
            mask[y2:y2 + self.method_parameters['cmd_block_size'],
            x2:x2 + self.method_parameters['cmd_block_size']] = 255

        return 'cmd', mask

    def ela_method(self, image_path):
        '''
        Error Level Analysis
        :param image_path:
        :return ela，图像形式的ELA分析结果:
        '''
        SCALE = 15
        cache_dir = self.cache_path_root or tempfile.gettempdir()
        os.makedirs(cache_dir, exist_ok=True)
        temp_file = None

        original = cv2.imread(image_path)
        if original is None:
            raise ValueError(f"failed to read image for ELA: {image_path}")
        with tempfile.NamedTemporaryFile(suffix='.jpg', dir=cache_dir, delete=False) as tmp:
            temp_file = tmp.name
        if not cv2.imwrite(temp_file, original, [cv2.IMWRITE_JPEG_QUALITY, 90]):
            raise ValueError(f"failed to write ELA temp file: {temp_file}")
        compressed = cv2.imread(temp_file)
        if compressed is None:
            raise ValueError(f"failed to read ELA temp file: {temp_file}")

        ela = cv2.absdiff(original, compressed) * SCALE
        # translate ela to mask
        mask = cv2.cvtColor(ela, cv2.COLOR_BGR2GRAY)
        try:
            if temp_file:
                os.remove(temp_file)
        except:
            pass
        return 'ela', mask

    def exif_method(self, image_path):
        '''
        检查图片的EXIF信息
        :param image_path:
        :return 可能的篡改信息:
        '''
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return 'exif', None

        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = value

        # 检查关键字段
        suspicious = []
        if 'Software' in exif and 'Photoshop' in exif['Software']:
            suspicious.append("使用了Photoshop进行修改")
        if 'DateTimeOriginal' != 'DateTime':
            suspicious.append("修改了拍摄或制作时间")

        return 'exif', suspicious if suspicious else 'exif', None

    def llm_method(self, image_path):
        # read image_path and transform to base64
        # 额度花完了（）
        # 先不用这个
        return None
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        client = OpenAI(
            api_key="sk-CXGzefLrCxYN4VKl1d35CeD7D9F4437dA72e61179594AfF4",
            base_url='https://api.mixrai.com/v1'
        )
        question = '你是一个学术造假检查专家，分析图片中是否有篡改、复制、拼接等学术造假问题。你的返回结果必须严格为一个介于0-10间的数字，0代表该图片没有任何造假痕迹，10代表该图片有非常严重的造假痕迹，不得返回除数字外的任何内容。'
        messages = [
            {
                "role": "Academic misconduct identification expert",
                "content": [
                    {"type": "text", "text":
                        f'{question}'},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        chat_response = completion
        answer = chat_response.choices[0].message.content
        print(answer)
        return answer
