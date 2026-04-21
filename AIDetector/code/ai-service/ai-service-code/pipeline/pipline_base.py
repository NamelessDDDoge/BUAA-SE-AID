
class PipelineBase:
    def __init__(self):
        self.images = []
        pass
    
    def run(self,images):
        raise NotImplementedError("run method not implemented")

    def get_results(self):
        raise NotImplementedError("get_results method not implemented")

    def get_methods_name(self):
        raise NotImplementedError("get_methods_name method not implemented")
        
    
    def clear_images(self):
        self.images.clear()
