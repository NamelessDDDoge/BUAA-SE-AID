# utils/image_saver.py
import os, uuid, numpy as np
from django.conf import settings
from PIL import Image

def save_ndarray_as_image(arr: np.ndarray,
                          subdir: str,
                          prefix: str = 'mask') -> str:
    """
    将 ndarray (H×W 或 H×W×3, float 0-1/0-255 或 uint8) 保存为 PNG，
    返回 MEDIA 相对路径（供 ImageField 赋值或手动拼 MEDIA_URL 使用）

    :param arr:      numpy 数组 (H, W) or (H, W, 3)
    :param subdir:   MEDIA_ROOT 下的子目录，如 'ela_results' 或 'masks'
    :param prefix:   文件名前缀
    :return:         形如 'ela_results/xxxxxxxx.png'
    """
    # 保证是 0-255 的 uint8
    if arr.dtype != np.uint8 and arr.ndim == 2 and subdir != 'ela_results':
        arr = arr.astype(np.float32)
        # arr = (255 * (arr - arr.min()) / (arr.ptp() or 1)).astype(np.uint8)
        # arr = (arr * 255).astype(np.uint8)

        # 二值化处理：0或255的单通道图像
        pred_binary = (arr >= 0.5).astype(np.uint8) * 255

        # 扩展为三通道 (H, W) -> (H, W, 3)
        arr = np.repeat(pred_binary[:, :, np.newaxis], repeats=3, axis=2)
    arr = arr.astype(np.uint8)

    # 灰度 → 3 通道可视化（可选；若要保持灰度可改 mode='L'）
    if arr.ndim == 2:
        img = Image.fromarray(arr, mode='L')
    else:
        # print(arr)
        img = Image.fromarray(arr)

    # 构造文件名 / 路径
    file_name      = f"{prefix}_{uuid.uuid4().hex}.png"
    relative_path  = os.path.join(subdir, file_name).replace("\\", "/")
    absolute_path  = os.path.join(settings.MEDIA_ROOT, relative_path)

    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
    img.save(absolute_path, format='PNG')

    return relative_path


if __name__ == '__main__':
    import pickle
    with open("llm_img_np.pkl", "rb") as f:
        data = pickle.load(f)
    save_ndarray_as_image(data, 'a')