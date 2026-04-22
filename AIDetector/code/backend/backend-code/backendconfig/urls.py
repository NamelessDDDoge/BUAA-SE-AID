from . import load_backend_config_module


_module = load_backend_config_module("_backendconfig_impl.urls", "urls.py")

urlpatterns = _module.urlpatterns
