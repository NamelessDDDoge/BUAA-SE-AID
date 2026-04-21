import argparse
import json
import shutil
from pathlib import Path

import cv2
import numpy as np


CLS_DICT = {
    "Microscopy": "microscopy",
    "Macroscopy": "macroscopy",
    "Blot/Gel": "blot",
    "FACS": "FACS",
}


def ensure_dirs(out_root: Path) -> None:
    for split in ("auth", "cstd", "mask"):
        for cls_name in CLS_DICT.values():
            (out_root / split / cls_name).mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def imread_unicode(path: Path):
    # OpenCV on Windows can fail on non-ASCII paths; decode from bytes instead.
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_unicode(path: Path, image: np.ndarray) -> None:
    ext = path.suffix or ".png"
    ok, buf = cv2.imencode(ext, image)
    if not ok:
        raise RuntimeError(f"Failed to encode image for {path}")
    buf.tofile(str(path))


def process_biofors(repo_root: Path, out_root: Path, mode: str = "all") -> dict:
    annotation_dir = repo_root / "annotation_files"
    images_dir = repo_root / "biofors_images"

    cls = load_json(annotation_dir / "classification.json")
    idd = load_json(annotation_dir / "idd_gt.json")
    cstd = load_json(annotation_dir / "cstd_gt.json")

    ensure_dirs(out_root)

    copied_auth = 0
    copied_cstd = 0
    copied_mask = 0
    missing = []

    if mode in ("all", "cstd", "mask"):
        for paper_id, images in cstd.items():
            for image_name, gt_boxes in images.items():
                cls_name = CLS_DICT[cls[paper_id][image_name]]
                src = images_dir / str(paper_id) / image_name
                dst = out_root / "cstd" / cls_name / f"{paper_id}-{image_name}"
                mask_dst = out_root / "mask" / cls_name / f"{paper_id}-{image_name}"
                if not src.exists():
                    missing.append(str(src))
                    continue
                if mode in ("all", "cstd"):
                    shutil.copy2(src, dst)
                    copied_cstd += 1
                if mode in ("all", "mask"):
                    img = imread_unicode(src)
                    if img is None:
                        missing.append(f"{src} [cv2 read failed]")
                        continue
                    mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
                    for points in gt_boxes:
                        x1, y1, x2, y2 = map(int, points)
                        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
                    imwrite_unicode(mask_dst, mask)
                    copied_mask += 1

    if mode in ("all", "auth"):
        for paper_id, images in cls.items():
            for image_name, class_name in images.items():
                if paper_id in cstd and image_name in cstd[paper_id]:
                    continue
                if paper_id in idd and image_name in idd[paper_id]:
                    continue

                cls_name = CLS_DICT[class_name]
                src = images_dir / str(paper_id) / image_name
                dst = out_root / "auth" / cls_name / f"{paper_id}-{image_name}"
                if not src.exists():
                    missing.append(str(src))
                    continue
                shutil.copy2(src, dst)
                copied_auth += 1

    return {
        "copied_auth": copied_auth,
        "copied_cstd": copied_cstd,
        "copied_mask": copied_mask,
        "missing_count": len(missing),
        "missing_samples": missing[:20],
        "out_root": str(out_root),
    }


def main():
    parser = argparse.ArgumentParser(description="Convert official BioFors data into URN training layout.")
    default_repo_root = Path(__file__).resolve().parents[2] / "BioFors"
    default_out_root = Path(__file__).resolve().parent / "BioFors"
    parser.add_argument("--repo-root", type=Path, default=default_repo_root)
    parser.add_argument("--out-root", type=Path, default=default_out_root)
    parser.add_argument(
        "--mode",
        choices=("all", "auth", "cstd", "mask"),
        default="all",
        help="Select which outputs to generate.",
    )
    args = parser.parse_args()

    result = process_biofors(args.repo_root, args.out_root, mode=args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
