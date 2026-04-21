import torch

def count_parameters_from_state_dict(state_dict):
    total_params = 0
    for tensor in state_dict.values():
        total_params += tensor.numel()  # numel() 返回张量的元素总数
    return total_params


checkpoint = torch.load("/root/autodl-tmp/SE/URN/logs/1745210081-2934208/checkpoint_9.pkl", map_location="cpu")
print(count_parameters_from_state_dict(checkpoint['model_state_dict']))