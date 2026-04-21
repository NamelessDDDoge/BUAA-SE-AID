import torch
import tqdm
import sys
print(sys.path)
import os
print(os.getcwd())
import cv2
import numpy as np

from factory.bio_data_factory import get_data, get_dataloader
from factory.hp_factory import get_hp
from factory.model_factory import get_model
from factory.optim_factory import get_optimizer
from easydict import EasyDict
import configs.coarse_bio_hyper_para
from torchvision.utils import make_grid
from utils.metric_collector import MetricCollector


def get_grid_img(img, pred, k=0.5):
    pred_255 = (pred >= k) * 255.0
    # print(pred_255)
    pred_255 = torch.repeat_interleave(pred_255, repeats=3, dim=0)
    show_list = [img, pred_255]
    grid_img = make_grid(show_list, nrow=2, padding=20, normalize=True,
                         scale_each=True, pad_value=1)
    np_grid_img = grid_img.detach().cpu().numpy()
    np_grid_img = np_grid_img.transpose(1, 2, 0)
    np_grid_img = (np_grid_img * 255).astype(np.uint8)
    return np_grid_img


def infer(network, img_dir, hyper_p, k=0.3):
    """
    Calculate metric values
    :param network: Network to use
    :param data_loader: Dataloader of test dataset
    :param hyper_p: Hyper parameters
    :param k: Threshold for calculating the metrics
    :return: Pixel-level and image-level metrics
    """
    from data.bio_infer_data import BioData
    bio_data = BioData(img_dir)
    img = bio_data.get()["img"]
    input_img = torch.unsqueeze(img, dim=0).cuda()
    # input_img = torch.unsqueeze(img, dim=0)
    network.eval()
    ans_img, ans_prob = None, None
    with torch.no_grad():
        # Feed a batch to the network
        net_out = network(input_img)
        # Update pixel-level metrics
        if hyper_p.loss.seg.enable:
            main_pred_flat = torch.sigmoid(net_out['seg']).float()[0]
            # print(main_pred_flat)
            # print(main_pred_flat.size())
            ans_img = main_pred_flat.detach().cpu().numpy()
            # ans_img = get_grid_img(img, main_pred_flat, k)

        # Update image-level metrics
        if hyper_p.loss.cls.enable:
            ans_prob = torch.sigmoid(net_out['cls']).float().view(-1)
        
        # ans_img = ans_img.detach().cpu().numpy()`
        ans_prob = ans_prob.detach().cpu().numpy()
    return (ans_img, ans_prob)



def infer_multi(network, img_dirs, hyper_p, k=0.3):
    """
    Calculate metric values
    :param network: Network to use
    :param data_loader: Dataloader of test dataset
    :param hyper_p: Hyper parameters
    :param k: Threshold for calculating the metrics
    :return: Pixel-level and image-level metrics
    """
    from data.bio_infer_data import BioData

    input_imgs = []

    for img_dir in img_dirs:
        bio_data = BioData(img_dir)
        img = bio_data.get()["img"]
        input_imgs.append(img)
    input_imgs = torch.stack(input_imgs)
    input_imgs = input_imgs.cuda()
    network.eval()
    ans_img, ans_prob = None, None
    with torch.no_grad():
        # Feed a batch to the network
        net_out = network(input_imgs)
        
        if hyper_p.loss.seg.enable:
            seg_output = torch.sigmoid(net_out['seg']).float()
            ans_img = seg_output.detach().cpu().numpy()

        # Update image-level metrics
        if hyper_p.loss.cls.enable:
            ans_prob = torch.sigmoid(net_out['cls']).float()
            ans_prob = ans_prob.detach().cpu()
            ans_prob = ans_prob.squeeze().tolist()
    ans = []
    if len(img_dirs) > 1:
        for cnt in range(len(ans_prob)):
            ans += (ans_img[cnt], ans_prob[cnt])
    else:
        ans.append((ans_img,ans_prob))
    return ans


def urn_initial_model(path:str):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path=os.path.join(current_dir,path);
    args = EasyDict({
        "train_set": None,
        "test_set": None,
        "gpu": 0,
        "seed": 42,
    })
    hp = get_hp(configs.coarse_bio_hyper_para.hp, args)
    net = get_model(hp)
    checkpoint = torch.load(model_path, map_location="cpu",
                            weights_only=False)
    net.load_state_dict(checkpoint['model_state_dict'])
    net = net.cuda()
    return net, hp


def urn_infer(image_path:str, net, hp, k_para):
    from configs.config import config_dict as config

    return infer_multi(net, image_path, hp, k_para)


if __name__ == '__main__':
    args = EasyDict({
        "train_set": None,
        "test_set": None,
        "gpu": 0,
        "seed": 42,
    })
    hp = get_hp(configs.coarse_bio_hyper_para.hp, args)
    net = get_model(hp)
    checkpoint = torch.load("/root/autodl-tmp/BUAA_SE_DetectFake/method/urn/weight/Coarse_v2.pkl", map_location="cpu",
                            weights_only=False)
    net.load_state_dict(checkpoint['model_state_dict'])
    net = net

    from configs.config import config_dict as config

    infer(net, "/root/autodl-tmp/BUAA_SE_DetectFake/test/img2.png", hp)