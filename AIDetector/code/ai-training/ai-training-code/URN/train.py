import argparse
import csv
import os
import time

import torch
import tqdm
from easydict import EasyDict

import configs.coarse_bio_hyper_para
from factory.bio_data_factory import get_data
from factory.hp_factory import get_hp
from factory.loss_factory import get_loss
from factory.model_factory import get_model
from factory.optim_factory import get_optimizer
from utils.metric_collector import MetricCollector


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def scalarize(value):
    if isinstance(value, torch.Tensor):
        return float(value.detach().cpu().item())
    return float(value)


def forward_batch(net, batch, hp):
    img = batch['img'].cuda(non_blocking=True)
    gt_mask = batch['mask'].unsqueeze(1).cuda(non_blocking=True).float()
    cls_gt = batch['cls'].cuda(non_blocking=True).float().view(-1)

    net_out = net(img)

    seg_loss = torch.tensor(0.0, device=img.device)
    cls_loss = torch.tensor(0.0, device=img.device)
    batch_loss = torch.tensor(0.0, device=img.device)

    if hp.loss.seg.enable:
        seg_loss = get_loss(net_out.seg.float(), gt_mask, hp.loss.seg)
        batch_loss = batch_loss + seg_loss

    if hp.loss.cls.enable:
        cls_loss = get_loss(net_out.cls.float().view(-1), cls_gt, hp.loss.cls)
        batch_loss = batch_loss + cls_loss

    return net_out, gt_mask, cls_gt, {
        "batch_loss": batch_loss,
        "seg_loss": seg_loss,
        "cls_loss": cls_loss,
    }


def update_metric_collector(metric_values, net_out, gt_mask, cls_gt, hp, threshold=0.5):
    if hp.loss.seg.enable:
        seg_pred = torch.sigmoid(net_out['seg']).float().view(-1)
        seg_true = gt_mask.float().view(-1)
        metric_values.update(seg_pred, seg_true, metric_type='seg', k=threshold)

    if hp.loss.cls.enable:
        cls_pred = torch.sigmoid(net_out['cls']).float().view(-1)
        metric_values.update(cls_pred, cls_gt.float().view(-1), metric_type='cls', k=threshold)


def finalize_metrics(metric_values, hp):
    metrics = {}
    if hp.loss.seg.enable:
        metrics.update(metric_values.show('seg'))
    if hp.loss.cls.enable:
        metrics.update(metric_values.show('cls'))
    return metrics


def run_epoch(net, data_loader, hp, optimizer=None, desc="train"):
    is_train = optimizer is not None
    metric_values = MetricCollector()
    total_loss = 0.0
    total_seg_loss = 0.0
    total_cls_loss = 0.0
    num_batches = 0

    iterator = tqdm.tqdm(data_loader, leave=False, desc=desc)
    for batch in iterator:
        if is_train:
            optimizer.zero_grad(set_to_none=True)
            net.train()
        else:
            net.eval()

        with torch.set_grad_enabled(is_train):
            net_out, gt_mask, cls_gt, loss_dict = forward_batch(net, batch, hp)
            if is_train:
                loss_dict['batch_loss'].backward()
                optimizer.step()

        update_metric_collector(metric_values, net_out, gt_mask, cls_gt, hp)
        total_loss += scalarize(loss_dict['batch_loss'])
        total_seg_loss += scalarize(loss_dict['seg_loss'])
        total_cls_loss += scalarize(loss_dict['cls_loss'])
        num_batches += 1

    metrics = finalize_metrics(metric_values, hp)
    metrics.update({
        "loss": total_loss / max(num_batches, 1),
        "seg_loss": total_seg_loss / max(num_batches, 1),
        "cls_loss": total_cls_loss / max(num_batches, 1),
    })
    return metrics


def setup_log_files(logs_dir):
    ensure_dir(logs_dir)
    checkpoints_dir = os.path.join(logs_dir, "checkpoints")
    ensure_dir(checkpoints_dir)
    metrics_csv = os.path.join(logs_dir, "metrics.csv")
    train_log = os.path.join(logs_dir, "train.log")
    return checkpoints_dir, metrics_csv, train_log


def append_log(train_log, message):
    print(message)
    with open(train_log, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def append_metrics_csv(metrics_csv, row):
    file_exists = os.path.exists(metrics_csv)
    with open(metrics_csv, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def save_checkpoint(checkpoints_dir, epoch, net, optimizer, train_metrics, test_metrics):
    ckpt_path = os.path.join(checkpoints_dir, f"checkpoint_epoch_{epoch:03d}.pkl")
    torch.save({
        "epoch": epoch,
        "model_state_dict": net.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
    }, ckpt_path)
    latest_path = os.path.join(checkpoints_dir, "latest.pkl")
    torch.save({
        "epoch": epoch,
        "model_state_dict": net.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
    }, latest_path)
    return ckpt_path


def load_checkpoint(resume_checkpoint, net, optimizer=None):
    checkpoint = torch.load(resume_checkpoint, map_location="cpu")
    net.load_state_dict(checkpoint["model_state_dict"])
    if optimizer is not None and "optimizer_state_dict" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint


def train_net(net, hp=None, config=None):
    if config is None:
        config = EasyDict()
    if hp is None:
        hp = EasyDict()

    checkpoints_dir, metrics_csv, train_log = setup_log_files(config.logs_dir)
    append_log(train_log, f"logs_dir={config.logs_dir}")
    append_log(train_log, f"checkpoints_dir={checkpoints_dir}")
    append_log(train_log, f"metrics_csv={metrics_csv}")
    append_log(train_log, f"train_set={hp.data.train}")
    append_log(train_log, f"test_set={hp.data.test}")
    append_log(train_log, f"batch_size={hp.train.batch_size}")
    append_log(train_log, f"epochs={hp.train.epochs}")

    train_loader = get_data(hp, config, 'train')
    test_loader = get_data(hp, config, 'test')
    optimizer = get_optimizer(hp, net)
    start_epoch = 1

    resume_checkpoint = getattr(config, "resume_checkpoint", None)
    if resume_checkpoint:
        checkpoint = load_checkpoint(resume_checkpoint, net, optimizer)
        start_epoch = int(checkpoint.get("epoch", 0)) + 1
        append_log(train_log, f"resume_checkpoint={resume_checkpoint}")
        append_log(train_log, f"resume_from_epoch={checkpoint.get('epoch', 'unknown')}")
        append_log(train_log, f"resume_next_epoch={start_epoch}")
        if start_epoch > hp.train.epochs:
            raise ValueError(
                f"Resume checkpoint is already at epoch {checkpoint.get('epoch')}, "
                f"but target epochs={hp.train.epochs}. Increase --epochs to at least {start_epoch}."
            )

    torch.cuda.empty_cache()
    t_epoch = tqdm.trange(start_epoch, hp.train.epochs + 1)

    for epoch in t_epoch:
        epoch_start = time.time()
        train_metrics = run_epoch(net, train_loader, hp, optimizer=optimizer, desc=f"train-{epoch}")
        test_metrics = run_epoch(net, test_loader, hp, optimizer=None, desc=f"test-{epoch}")
        ckpt_path = save_checkpoint(checkpoints_dir, epoch, net, optimizer, train_metrics, test_metrics)

        log_row = {
            "epoch": epoch,
            "seconds": round(time.time() - epoch_start, 2),
            "train_loss": round(train_metrics["loss"], 6),
            "train_seg_loss": round(train_metrics["seg_loss"], 6),
            "train_cls_loss": round(train_metrics["cls_loss"], 6),
            "train_f1_seg": round(train_metrics.get("f1_seg", 0.0), 6),
            "train_mcc_seg": round(train_metrics.get("mcc_seg", 0.0), 6),
            "train_auc_cls": round(train_metrics.get("auc_cls", 0.0), 6),
            "train_acc_cls": round(train_metrics.get("acc_cls", 0.0), 6),
            "test_loss": round(test_metrics["loss"], 6),
            "test_seg_loss": round(test_metrics["seg_loss"], 6),
            "test_cls_loss": round(test_metrics["cls_loss"], 6),
            "test_f1_seg": round(test_metrics.get("f1_seg", 0.0), 6),
            "test_mcc_seg": round(test_metrics.get("mcc_seg", 0.0), 6),
            "test_auc_cls": round(test_metrics.get("auc_cls", 0.0), 6),
            "test_acc_cls": round(test_metrics.get("acc_cls", 0.0), 6),
            "checkpoint": ckpt_path,
        }
        append_metrics_csv(metrics_csv, log_row)
        append_log(train_log, str(log_row))
        t_epoch.set_description(f"epoch={epoch} train_loss={train_metrics['loss']:.4f} test_loss={test_metrics['loss']:.4f}")

    append_log(train_log, "training_finished")
    return {
        "logs_dir": config.logs_dir,
        "checkpoints_dir": checkpoints_dir,
        "metrics_csv": metrics_csv,
        "train_log": train_log,
    }


def build_default_logs_dir():
    run_name = f"full_train_{str(time.time()).replace('.', '-')}"
    from configs.config import config_dict
    return os.path.join(config_dict.base_dir if hasattr(config_dict, "base_dir") else os.path.dirname(__file__), "logs", run_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-set", default="train_splicing")
    parser.add_argument("--test-set", default="test_splicing")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--logs-dir", default=None)
    parser.add_argument("--resume-checkpoint", default=None)
    parser.add_argument("--coarse-checkpoint", default=None)
    args = parser.parse_args()

    hp_args = EasyDict({
        "train_set": args.train_set,
        "test_set": args.test_set,
        "gpu": 0,
        "seed": 42,
    })
    hp = get_hp(configs.coarse_bio_hyper_para.hp, hp_args)
    hp.train.epochs = args.epochs
    hp.train.batch_size = args.batch_size
    hp.coarse_checkpoint = args.coarse_checkpoint

    from configs.config import config_dict as config
    default_logs_dir = os.path.join(os.path.dirname(__file__), "logs", f"full_train_{str(time.time()).replace('.', '-')}")
    if args.resume_checkpoint and args.logs_dir is None:
        config.logs_dir = os.path.dirname(os.path.dirname(os.path.abspath(args.resume_checkpoint)))
    else:
        config.logs_dir = args.logs_dir or default_logs_dir
    config.data_txt_dir = os.path.join(os.path.dirname(__file__), "data")
    config.bio_data_txt_dir = os.path.join(os.path.dirname(__file__), "data")
    config.save_checkpoint = True
    config.checkpoint_epochs = 1
    config.eval_epochs = 1
    config.resume_checkpoint = args.resume_checkpoint

    model_coarse_path = args.coarse_checkpoint
    if args.resume_checkpoint and hp.model.find("Fine") != -1 and model_coarse_path is None:
        model_coarse_path = None
    net = get_model(hp, coarse_path=model_coarse_path).cuda()
    train_net(net, hp, config)
