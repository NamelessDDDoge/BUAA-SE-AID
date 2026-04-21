import time

import easydict
import random
import cv2
import numpy as np
import albumentations as alb
import albumentations.pytorch as albp
import os.path as osp
import torch.nn.functional as F
from torch.utils.data import DataLoader
import torch
from torchvision.utils import make_grid


def get_grid_img(img, gt, pred, k=0.5):
    gt_255 = gt * 255.0
    print(gt_255)
    gt_255 = torch.repeat_interleave(gt_255, repeats=3, dim=0)
    pred_255 = (pred >= k) * 255.0
    print(pred_255)
    pred_255 = torch.repeat_interleave(pred_255, repeats=3, dim=0)
    show_list = [img, gt_255, pred_255]
    grid_img = make_grid(show_list, nrow=3, padding=20, normalize=True,
                         scale_each=True, pad_value=1)
    np_grid_img = grid_img.detach().cpu().numpy()
    np_grid_img = np_grid_img.transpose(1, 2, 0)
    return np_grid_img


def get_img_and_mask(img_dir, mask_dir, cls_index, keep_scale=False):
    """
    :param cls_index: 1 = spliced, 0 = pristine
    :param img_dir: Path of image file
    :param mask_dir: Path of mask file
    :return: a dict with keys 'img', 'mask'
    """
    img = cv2.imread(img_dir)
    try:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if mask_dir == 'None':
            try:
                if cls_index == 0:
                    mask = np.zeros((img.shape[0], img.shape[1]))
                else:
                    mask = np.ones((img.shape[0], img.shape[1])) * 255
            except AttributeError:
                print(img_dir, mask_dir)
                if cls_index == 0:
                    mask = np.zeros((img.shape[0], img.shape[1]))
                else:
                    mask = np.ones((img.shape[0], img.shape[1])) * 255
        else:
            mask = cv2.imread(mask_dir, cv2.IMREAD_GRAYSCALE)

    except ValueError:
        print(img_dir, mask_dir)
    try:
        return {
            "img": np.array(img),
            "mask": np.array(mask)
        }
    except UnboundLocalError:
        print(img_dir)
        print(mask_dir)


class BioData:

    def __init__(self,
                 img_dir,
                 img_size=256,
                 keep_scale=False,
                 ):
        self.split = "test"
        self.img_list = [img_dir]
        self.mask_list = ["None"]
        self.cls_list = [0]
        self.keep_scale = keep_scale
        """testing data augment"""
        function_list = []
        function_list.extend([
            alb.Resize(img_size, img_size, interpolation=cv2.INTER_NEAREST),
            alb.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            albp.transforms.ToTensorV2(),
        ])
        self.transforms = alb.Compose(
            function_list
        )

        self.original_mask_transform = alb.Compose([])


    def read_img_mask(self, index):
        this_img = self.img_list[index]
        this_mask = self.mask_list[index]
        this_cls = int(self.cls_list[index])
        x = get_img_and_mask(this_img, this_mask, this_cls, self.keep_scale)  # 预处理图像和mask
        return x

    # @torchsnooper.snoop()
    def get(self):
        x = self.read_img_mask(0)
        if x['img'].shape[:2] != x['mask'].shape[:2]:
            print(f"Warning: Resizing mask to match image")
            x['mask'] = cv2.resize(
                x['mask'],
                (x['img'].shape[1], x['img'].shape[0]),  # (width, height)
                interpolation=cv2.INTER_NEAREST  # 对于 mask 通常用最近邻插值
            )

        """进行数据增强"""
        try:
            aug = self.transforms(image=x['img'], mask=x['mask'])
        except:
            print(x['img'])
            print(x['mask'])
            print(self.img_list[0], self.mask_list[0])
            raise ValueError
        img = aug['image']
        mask = aug['mask'] / 255.0

        res_dict = easydict.EasyDict({
            "img": img,
            "mask": mask,
            "cls": torch.max(mask),
        })

        res_dict['original_mask'] = x['mask'] / 255.0

        return res_dict
