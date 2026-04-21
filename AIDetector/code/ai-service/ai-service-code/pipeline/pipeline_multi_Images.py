import os.path

from pipeline.pipline_base import PipelineBase
from method.MultiImagesMethod import *


class PipelineMultiImages(PipelineBase):
    def __init__(self):
        super().__init__()
        self.results = []
        self.multiImagesMethod = MultiImagesMethod()

    def run(self,images):
        self.images = images
        assert len(self.images) == 1, "This pipeline only supports single image"
        image = self.images[0]
        cache_path_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'cache'))
        os.makedirs(cache_path_root, exist_ok=True)
        image_path = os.path.join(cache_path_root, 'image.jpg')
        cv2.imwrite(image_path, image)
        method = self.multiImagesMethod.get_methods()
        self.multiImagesMethod.set_cache_path_root(cache_path_root)
        for m in method:
            name, result = m(image_path)
            self.results.append((name, result))

    def get_results(self):
        return self.results
    