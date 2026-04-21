import torch
import tqdm
from utils.metric_collector import MetricCollector

from factory.bio_data_factory import get_data, get_dataloader
from factory.hp_factory import get_hp
from factory.model_factory import get_model
from factory.optim_factory import get_optimizer
from easydict import EasyDict
import configs.coarse_bio_hyper_para
import configs.fine_bce_bio_hyper_para

def eval_after_train(network, data_loader, hyper_p, k=0.5):
    """
    Calculate metric values
    :param network: Network to use
    :param data_loader: Dataloader of test dataset
    :param hyper_p: Hyper parameters
    :param k: Threshold for calculating the metrics
    :return: Pixel-level and image-level metrics
    """
    metric_values = MetricCollector()
    # Stop gradients
    network.eval()
    with torch.no_grad():
        for idx, batch in enumerate(tqdm.tqdm(data_loader)):
            # Feed a batch to the network
            # net_out = network(batch['img'].cuda())
            net_out = network(batch['img'])
            # Update pixel-level metrics
            if hyper_p.loss.seg.enable:
                main_pred_flat = torch.sigmoid(net_out['seg']).float().view(-1)
                main_true_flat = batch['mask'].float().view(-1)
                metric_values.update(main_pred_flat, main_true_flat, data_loader.batch_size, 'seg', k)

            # Update image-level metrics
            if hyper_p.loss.cls.enable:
                cls_pred_flat = torch.sigmoid(net_out['cls']).float().view(-1)
                cls_true_flat = batch['cls'].float().view(-1)
                metric_values.update(cls_pred_flat, cls_true_flat, data_loader.batch_size, 'cls', k)

    # Output metric values
    seg_res = metric_values.show('seg')
    print(metric_values.metrics.seg.f1_seg.avg, metric_values.metrics.seg.mcc_seg.avg)

    cls_res = metric_values.show('cls')
    print(metric_values.metrics.cls.auc_cls.avg, metric_values.metrics.cls.acc_cls.avg)
    print('\n')

    return seg_res, cls_res


if __name__ == '__main__':
    # args = EasyDict({
    #     "train_set": None,
    #     "test_set": None,
    #     "gpu": 0,
    #     "seed": 42,
    # })
    # hp = get_hp(configs.coarse_bio_hyper_para.hp, args)
    # net = get_model(hp)
    # checkpoint = torch.load("/root/autodl-tmp/SE/URN/logs/1744574122-6448226/checkpoint_179.pkl", map_location="cpu")
    # net.load_state_dict(checkpoint['model_state_dict'])
    # net = net.cuda()

    # from configs.config import config_dict as config

    # test_loaders = get_data(hp, config, 'test')
    # eval_after_train(net, test_loaders, hp)

    # args = EasyDict({
    #     "train_set": None,
    #     "test_set": None,
    #     "gpu": 0,
    #     "seed": 42,
    # })
    # hp = get_hp(configs.fine_bce_bio_hyper_para.hp, args)
    # net = get_model(hp)
    # checkpoint = torch.load("/root/autodl-tmp/SE/URN/logs/1745155504-1374629/checkpoint_89.pkl", map_location="cpu")
    # net.load_state_dict(checkpoint['model_state_dict'])
    # net = net.cuda()

    # from configs.config import config_dict as config

    # test_loaders = get_data(hp, config, 'test')
    # eval_after_train(net, test_loaders, hp)

    args = EasyDict({
        "train_set": None,
        "test_set": None,
        "gpu": 0,
        "seed": 42,
    })
    hp = get_hp(configs.coarse_bio_hyper_para.hp, args)
    net = get_model(hp)
    checkpoint = torch.load("/root/autodl-tmp/SE/URN/logs/contrast/checkpoint_199.pkl", map_location="cpu", weights_only=True)
    net.load_state_dict(checkpoint['model_state_dict'])
    # net = net.cuda()
    import time
    # time.sleep(60)

    from configs.config import config_dict as config

    test_loaders = get_data(hp, config, 'test')
    eval_after_train(net, test_loaders, hp)