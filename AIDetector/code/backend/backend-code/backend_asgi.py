from backend_config_loader import load_backend_config_module


_module = load_backend_config_module("_backend_config_impl.asgi", "asgi.py")

for _name in dir(_module):
    if _name.startswith("__") and _name not in {"__doc__"}:
        continue
    globals()[_name] = getattr(_module, _name)
