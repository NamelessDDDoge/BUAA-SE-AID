import os.path
import json
from pathlib import Path

from pipeline.pipline_base import PipelineBase
from method.SingleImageMethod import *
from concurrent.futures import ProcessPoolExecutor, as_completed
import shutil


ASCII_CACHE_ROOT = Path.home() / ".codex" / "memories" / "ai_image_cache"


class PipelineSingleImage(PipelineBase):
    def __init__(self):
        super().__init__()
        self.singleImageMethod = SingleImageMethod()

    def run(self,images):
        self.images = images
        # print(images.shape)
        assert len(self.images) == 1, "This pipeline only supports single image"
        image = self.images[0]
        cache_path_root = str(ASCII_CACHE_ROOT)
        os.makedirs(cache_path_root, exist_ok=True)
        image_path = os.path.join(cache_path_root, 'image.jpg')
        cv2.imwrite(image_path, image)
        method = self.singleImageMethod.get_methods()
        self.singleImageMethod.set_cache_path_root(cache_path_root)
        results = []
        for m in method:
            name, result = m(image_path)
            results.append((name, result))
        self.results.append(results)
    
    def run_multi_images(self, images):
        self.results = []        
        cache_path_root = str(ASCII_CACHE_ROOT)
        # 如果 cache 目录已存在，则先删除它及其所有内容
        if os.path.exists(cache_path_root):
            shutil.rmtree(cache_path_root)
        os.makedirs(cache_path_root, exist_ok=True)
        image_pathes = []
        cnt = 0
        for img in images:
            image_path = os.path.join(cache_path_root, f'image_{cnt}.jpg')
            cnt += 1
            image_pathes.append(image_path)
            cv2.imwrite(image_path, img)
        for m in self.singleImageMethod.get_methods():
            name, results = m(image_pathes)
            self.results.append((name, results))

    def get_results(self):
        return self.results

    def change_method_parameters(self, method_name, parameters):
        if method_name in self.singleImageMethod.method_parameters:
            self.singleImageMethod.method_parameters[method_name] = parameters
        else:
            raise ValueError(f"Method {method_name} not found in available methods.")
    
    def set_method_parameters(self, parameters):
        self.singleImageMethod.set_method_parameters(parameters)
        
    def save_method_parameters(self):
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(self.singleImageMethod.method_parameters, f, ensure_ascii=False, indent=4)

    def get_method_parameters_name_and_type(self):
        return self.singleImageMethod.get_method_parameters_name_and_type()

    def get_methods_name(self):
        return self.singleImageMethod.get_methods_name()
