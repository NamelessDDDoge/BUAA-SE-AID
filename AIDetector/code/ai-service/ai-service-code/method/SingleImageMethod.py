import base64

from skimage.feature import match_template
import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
import os
import sys
import random
import tempfile
from openai import OpenAI
import os
import subprocess
import json
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from Config import get_method_switches, is_method_enabled

current_dir = os.path.dirname(os.path.abspath(__file__))
# 构造项目c的绝对路径
project_c_path = os.path.join(current_dir, "urn")
# 将项目c的路径添加到Python搜索路径最前
sys.path.insert(0, project_c_path)
from infer import urn_initial_model, urn_infer


class SingleImageMethod:
    def __init__(self):
        self.method_parameters = {'cmd_block_size': 64, 'urn_k': 0.3, 'if_use_llm': True}
        self.method_switches_override = None
        self.cache_path_root = ''
        self.coarse_v2_net, self.coarse_v2_hp = self._init_urn_model_if_enabled(
            'urn_coarse_v2', "weight/Coarse_v2.pkl"
        )
        self.blur_net, self.blur_hp = self._init_urn_model_if_enabled(
            'urn_blurring', "weight/blurring.pkl"
        )
        self.brute_net, self.brute_hp = self._init_urn_model_if_enabled(
            'urn_brute_force', "weight/brute_force.pkl"
        )
        self.contrast_net, self.contrast_hp = self._init_urn_model_if_enabled(
            'urn_contrast', "weight/contrast.pkl"
        )
        self.inpating_net, self.inpating_hp = self._init_urn_model_if_enabled(
            'urn_inpainting', "weight/inpainting.pkl"
        )

    def set_cache_path_root(self, cache_path_root):
        self.cache_path_root = cache_path_root

    def set_method_parameters(self, parameters):
        normalized = dict(parameters or {})
        switches = normalized.pop('method_switches', None)
        self.method_parameters.update(normalized)
        self.method_switches_override = self._normalize_method_switches(switches)

    def get_methods(self):
        return [
            method
            for name, method in self.get_method_map()
            if self._is_method_enabled(name)
        ]

    def get_methods_name(self):
        return [
            name
            for name, _ in self.get_method_map()
            if self._is_method_enabled(name)
        ]

    def get_method_map(self):
        return [
            ('llm', self.llm_method),
            ('ela', self.ela_method),
            ('exif', self.exif_method),
            ('cmd', self.cmd_method),
            ('urn_coarse_v2', self.urn_coarse_v2_method),
            ('urn_blurring', self.urn_blur_method),
            ('urn_brute_force', self.urn_brute_method),
            ('urn_contrast', self.urn_contrast_method),
            ('urn_inpainting', self.urn_inpating_method),
        ]

    def _init_urn_model_if_enabled(self, method_name, weight_path):
        if not is_method_enabled('single_image', method_name):
            return None, None
        return urn_initial_model(weight_path)

    def _normalize_method_switches(self, switches):
        if not isinstance(switches, dict):
            return None
        default_switches = get_method_switches('single_image').copy()
        for name in default_switches:
            if name in switches:
                default_switches[name] = bool(switches[name])
        return default_switches

    def _is_method_enabled(self, method_name):
        if self.method_switches_override is not None:
            return self.method_switches_override.get(method_name, False)
        return is_method_enabled('single_image', method_name)

    def get_method_parameters_name_and_type(self):
        # automatically get method parameters name and type
        key = self.method_parameters.keys()
        value = self.method_parameters.values()
        type = []
        for v in value:
            if isinstance(v, int):
                type.append('int')
            elif isinstance(v, float):
                type.append('float')
            elif isinstance(v, str):
                type.append('str')
            elif isinstance(v, list):
                type.append('list')
            else:
                type.append('unknown')
        return key, type

    def urn_coarse_v2_method(self, image_path):
        return 'urn_coarse_v2', urn_infer(image_path, self.coarse_v2_net, self.coarse_v2_hp, self.method_parameters['urn_k'])
    
    def urn_blur_method(self, image_path):
        return 'urn_blurring', urn_infer(image_path, self.blur_net, self.blur_hp, self.method_parameters['urn_k'])
    
    def urn_brute_method(self, image_path):
        return 'urn_brute_force', urn_infer(image_path, self.brute_net, self.brute_hp, self.method_parameters['urn_k'])
    
    def urn_contrast_method(self, image_path):
        return 'urn_contrast', urn_infer(image_path, self.contrast_net, self.contrast_hp, self.method_parameters['urn_k'])
    
    def urn_inpating_method(self, image_path):
        return 'urn_inpainting', urn_infer(image_path, self.inpating_net, self.inpating_hp, self.method_parameters['urn_k'])

    def cmd_method(self, image_paths):
        def _process(path):
            print(path)
            img = cv2.imread(path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            matches = []

            bs = self.method_parameters['cmd_block_size']
            step = bs // 2
            for y in range(0, h - bs, step):
                for x in range(0, w - bs, step):
                    block = gray[y:y + bs, x:x + bs]
                    result = match_template(gray, block)
                    loc = np.where(result >= 0.9)
                    for pt in zip(*loc[::-1]):
                        if abs(pt[0] - x) > bs or abs(pt[1] - y) > bs:
                            matches.append((x, y, pt[0], pt[1]))

            mask = np.zeros_like(gray)
            for x1, y1, x2, y2 in matches:
                mask[y1:y1 + bs, x1:x1 + bs] = 255
                mask[y2:y2 + bs, x2:x2 + bs] = 255

            return mask
        ans_list = []
        with ThreadPoolExecutor() as executor:
            # executor.map 返回的是一个生成器，按顺序对应每个 image_paths
            results = executor.map(_process, image_paths)
            # zip 会把 (path, result) 一一对应
            for path, mask in zip(image_paths, results):
                ans_list.append((path, mask))
        return 'cmd', ans_list

    def ela_method(self, image_paths):
        '''
        Error Level Analysis
        :param image_path:
        :return ela，图像形式的ELA分析结果:
        '''
        def _process(image_path):
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
            return mask
        
        ans_list = []
        with ThreadPoolExecutor() as executor:
            # executor.map 返回的是一个生成器，按顺序对应每个 image_paths
            results = executor.map(_process, image_paths)
            # zip 会把 (path, result) 一一对应
            for path, mask in zip(image_paths, results):
                ans_list.append((path, mask))
        return 'ela', ans_list

    def exif_method(self, image_paths):
        '''
        检查图片的EXIF信息
        :param image_path:
        :return 可能的篡改信息:
        '''
        def _process(image_path):
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
        ans_list = []
        with ThreadPoolExecutor() as executor:
            # executor.map 返回的是一个生成器，按顺序对应每个 image_paths
            results = executor.map(_process, image_paths)
            # zip 会把 (path, result) 一一对应
            for path, mask in zip(image_paths, results):
                ans_list.append((path, mask))
        return 'exif', ans_list
    
    def llm_method(self, image_paths):
        results = []
        for image_path in image_paths:
            results.append((image_path,self.llm_method_single(image_path)))
        return 'llm', results
                           
    def llm_method_single(self, image_path):
        # read image_path and transform to base64
        # 额度花完了（）
        # 先不用这个
        # 获取当前脚本所在目录
        if not self.method_parameters['if_use_llm']:
            return None
        import os
        import shutil
        current_dir = os.path.dirname(os.path.abspath(__file__))
        current_dir = os.path.join(current_dir, 'llm')

        # 定义路径变量
        WEIGHT_PATH = os.path.join(current_dir, 'weight/fakeshield-v1-22b')
        IMAGE_PATH = image_path
        DTE_FDM_OUTPUT = os.path.join(current_dir, 'playground/DTE-FDM_output.jsonl')
        MFLM_OUTPUT = os.path.join(current_dir, 'playground/MFLM_output')
        
        # 清空MFLM输出目录
        if os.path.exists(MFLM_OUTPUT):
            shutil.rmtree(MFLM_OUTPUT)
        os.makedirs(MFLM_OUTPUT, exist_ok=True)

        # 虚拟环境路径
        venv_python = '/root/miniconda3/envs/llm/bin/python'
        venv_pip = '/root/miniconda3/envs/llm/bin/pip'

        # 设置环境变量
        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = '0'

        try:
            # 安装第一个版本的transformers
            subprocess.check_call(
                [venv_pip, 'install', '-q', 'transformers==4.37.2'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # 运行第一个命令
            cmd_dte = [
                venv_python,
                '-m',
                'llava.serve.cli',
                '--model-path', os.path.join(WEIGHT_PATH, 'DTE-FDM'),
                '--DTG-path', os.path.join(WEIGHT_PATH, 'DTG.pth'),
                '--image-path', IMAGE_PATH,
                '--output-path', DTE_FDM_OUTPUT
            ]
            subprocess.check_call(cmd_dte, cwd=current_dir, env=env)

            # 安装第二个版本的transformers
            subprocess.check_call(
                [venv_pip, 'install', '-q', 'transformers==4.28.0'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # 运行第二个命令
            cmd_mflm = [
                venv_python,
                os.path.join(current_dir, 'MFLM/cli_demo.py'),
                '--version', os.path.join(WEIGHT_PATH, 'MFLM'),
                '--DTE-FDM-output', DTE_FDM_OUTPUT,
                '--MFLM-output', MFLM_OUTPUT
            ]
            subprocess.check_call(cmd_mflm, cwd=current_dir, env=env)

            # 读取DTE输出
            dte_content = None
            if os.path.exists(DTE_FDM_OUTPUT):
                with open(DTE_FDM_OUTPUT, 'r') as f:
                    for line in f:
                        dte_content = json.loads(line)['outputs']

            # 读取图片文件
            import os
            import glob
            import numpy as np
            from PIL import Image

            # 读取图片文件
            image_data = {}
            image_patterns = ['*.jpg', '*.jpeg', '*.png']
            image_patterns = ['*.jpg', '*.jpeg', '*.png']
            for pattern in image_patterns:
                for img_path in glob.glob(os.path.join(MFLM_OUTPUT, pattern)):
                    with Image.open(img_path) as img:
                        img_array = np.array(img)
                        return (dte_content, img_array)
            # 如果没有找到任何图片
            return (dte_content, None)

        except subprocess.CalledProcessError as e:
            return {'error': f'Command failed with code {e.returncode}'}
        except Exception as e:
            return {'error': str(e)}
        return 'If you read this, there are some problems. Call jzy.'
        # with open(image_path, "rb") as image_file:
        #     base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        # client = OpenAI(
        #     api_key="sk-CXGzefLrCxYN4VKl1d35CeD7D9F4437dA72e61179594AfF4",
        #     base_url='https://api.mixrai.com/v1'
        # )
        # question = '你是一个学术造假检查专家，分析图片中是否有学术造假问题。你的返回结果必须严格为三个个介于0-10间的数字，分别代表对篡改、复制、拼接的评判结果。0代表该图片没有任何造假痕迹，10代表该图片有非常严重的造假痕迹，不得返回除数字外的任何内容。'
        # messages = [
        #     {
        #         "role": "Academic misconduct identification expert",
        #         "content": [
        #             {"type": "text", "text":
        #                 f'{question}'},
        #             {
        #                 "type": "image_url",
        #                 "image_url": {
        #                     "url": f"data:image/png;base64,{base64_image}"
        #                 }
        #             }
        #         ]
        #     }
        # ]
        # completion = client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=messages
        # )
        # chat_response = completion
        # answer = chat_response.choices[0].message.content
        # print(answer)
        # return answer

