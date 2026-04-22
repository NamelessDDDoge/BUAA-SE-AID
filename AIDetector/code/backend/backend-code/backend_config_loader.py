from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


CONFIG_DIR = Path(__file__).resolve().parent / "backend-config"


def load_backend_config_module(alias: str, file_name: str):
    module = sys.modules.get(alias)
    if module is not None:
        return module

    module_path = CONFIG_DIR / file_name
    spec = spec_from_file_location(alias, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load backend config module: {module_path}")

    module = module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module
