SINGLE_IMAGE_METHOD_SWITCHES = {
    "llm": False,
    "ela": False,
    "exif": False,
    "cmd": False,
    "urn_coarse_v2": True,
    "urn_blurring": False,
    "urn_brute_force": False,
    "urn_contrast": False,
    "urn_inpainting": False,
}


MULTI_IMAGES_METHOD_SWITCHES = {
    "llm": False,
    "ela": False,
    "exif": False,
    "cmd": False,
}


def get_method_switches(method_group):
    if method_group == "single_image":
        return SINGLE_IMAGE_METHOD_SWITCHES
    if method_group == "multi_images":
        return MULTI_IMAGES_METHOD_SWITCHES
    raise ValueError(f"Unknown method group: {method_group}")


def is_method_enabled(method_group, method_name):
    return get_method_switches(method_group).get(method_name, False)
