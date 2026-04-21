from URN.coarse_net import get_coarse_net
from URN.fine_net import get_fine_net


DEFAULT_FINE_COARSE_CHECKPOINT = "/root/autodl-tmp/SE/URN/logs/1745188328-4204717/checkpoint_199.pkl"


def get_model(hyper_para, coarse_path=None):
    """
    Get network
    :param hyper_para: hyperparameters
    :return: Network
    """
    model_name = hyper_para.model
    model_dict = {
        "Coarse": get_coarse_net,
        "Fine": get_fine_net,
    }
    if model_name.find('Fine') == -1:
        net_model = model_dict[model_name]()
    else:
        fine_coarse_path = coarse_path
        if fine_coarse_path is None:
            fine_coarse_path = getattr(hyper_para, "coarse_checkpoint", DEFAULT_FINE_COARSE_CHECKPOINT)
        net_model = model_dict[model_name](fine_coarse_path)

    return net_model
