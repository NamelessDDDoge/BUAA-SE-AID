from . import load_backend_config_module


_module = load_backend_config_module("_backendconfig_impl.asgi", "asgi.py")

application = _module.application
