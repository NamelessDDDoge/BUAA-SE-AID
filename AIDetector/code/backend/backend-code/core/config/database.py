import atexit
import logging
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


_DB_TUNNEL = None
logger = logging.getLogger(__name__)


def build_database_settings(project_dir: Path, env_get, env_bool, env_int):
    mode = (env_get("DATABASE_MODE", "local") or "local").strip().lower()

    if mode == "local":
        db_name = env_get("LOCAL_DB_NAME") or env_get("DB_NAME") or "db.sqlite3"
        db_path = Path(db_name)
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": db_path if db_path.is_absolute() else project_dir / db_name,
            }
        }

    if mode == "aliyun_postgres":
        try:
            return {"default": _build_aliyun_postgres_settings(env_get, env_bool, env_int)}
        except Exception as exc:
            fallback = _build_fallback_database_settings(project_dir, env_get)
            if fallback is None:
                raise
            logger.warning(
                "Aliyun Postgres database configuration failed; falling back to %s. Error: %s",
                fallback["ENGINE"],
                exc,
            )
            return {"default": fallback}

    if mode == "custom":
        return {"default": _build_custom_database_settings(project_dir, env_get)}

    raise ImproperlyConfigured(
        f"Unsupported DATABASE_MODE '{mode}'. Expected one of: local, aliyun_postgres, custom."
    )


def _build_custom_database_settings(project_dir: Path, env_get):
    database_engine = env_get("DB_ENGINE")
    database_name = env_get("DB_NAME")

    if database_engine:
        config = {
            "ENGINE": database_engine,
            "NAME": database_name or "backend_project",
        }
        if database_engine == "django.db.backends.sqlite3":
            db_name = database_name or "db.sqlite3"
            db_path = Path(db_name)
            config["NAME"] = db_path if db_path.is_absolute() else project_dir / db_name
        else:
            config.update(
                {
                    "USER": env_get("DB_USER", ""),
                    "PASSWORD": env_get("DB_PASSWORD", ""),
                    "HOST": env_get("DB_HOST", "127.0.0.1"),
                    "PORT": env_get("DB_PORT", "3306"),
                }
            )
            db_charset = env_get("DB_CHARSET")
            if db_charset:
                config["OPTIONS"] = {"charset": db_charset}
        return config

    if env_get("MYSQL_NAME"):
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env_get("MYSQL_NAME"),
            "USER": env_get("MYSQL_USER", ""),
            "PASSWORD": env_get("MYSQL_PASSWORD", ""),
            "HOST": env_get("MYSQL_HOST", "127.0.0.1"),
            "PORT": env_get("MYSQL_PORT", "3306"),
        }

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": project_dir / "db.sqlite3",
    }


def _build_fallback_database_settings(project_dir: Path, env_get):
    if env_get("DB_ENGINE") or env_get("MYSQL_NAME"):
        return _build_custom_database_settings(project_dir, env_get)

    local_db_name = env_get("LOCAL_DB_NAME")
    if not local_db_name:
        return None

    db_path = Path(local_db_name)
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": db_path if db_path.is_absolute() else project_dir / local_db_name,
    }


def _build_aliyun_postgres_settings(env_get, env_bool, env_int):
    host = _require_env(env_get, "ALIYUN_DB_HOST")
    port = env_int("ALIYUN_DB_PORT", 5432)

    if env_bool("ALIYUN_DB_USE_SSH_TUNNEL", False):
        host, port = _start_aliyun_db_tunnel(env_get, env_int, port)

    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _require_env(env_get, "ALIYUN_DB_NAME"),
        "USER": _require_env(env_get, "ALIYUN_DB_USER"),
        "PASSWORD": _require_env(env_get, "ALIYUN_DB_PASSWORD"),
        "HOST": host,
        "PORT": str(port),
    }

    connect_timeout = env_get("ALIYUN_DB_CONNECT_TIMEOUT")
    if connect_timeout:
        config["OPTIONS"] = {"connect_timeout": int(connect_timeout)}

    return config


def _start_aliyun_db_tunnel(env_get, env_int, remote_port: int):
    global _DB_TUNNEL

    if _DB_TUNNEL is not None and getattr(_DB_TUNNEL, "is_active", False):
        return "127.0.0.1", _DB_TUNNEL.local_bind_port

    try:
        from sshtunnel import SSHTunnelForwarder
    except ImportError as exc:
        raise ImproperlyConfigured(
            "ALIYUN_DB_USE_SSH_TUNNEL=True requires the 'sshtunnel' package."
        ) from exc

    ssh_host = _require_env(env_get, "ALIYUN_SSH_HOST")
    ssh_user = _require_env(env_get, "ALIYUN_SSH_USER")
    ssh_port = int(env_get("ALIYUN_SSH_PORT", 22))
    ssh_password = env_get("ALIYUN_SSH_PASSWORD")
    ssh_private_key = env_get("ALIYUN_SSH_PRIVATE_KEY")

    tunnel_kwargs = {
        "ssh_username": ssh_user,
        "remote_bind_address": (_require_env(env_get, "ALIYUN_DB_HOST"), remote_port),
        "local_bind_address": (
            env_get("ALIYUN_DB_LOCAL_HOST", "127.0.0.1"),
            env_int("ALIYUN_DB_LOCAL_PORT", 5433),
        ),
        "allow_agent": False,
        "host_pkey_directories": [],
    }

    if ssh_private_key:
        tunnel_kwargs["ssh_pkey"] = ssh_private_key
    elif ssh_password:
        tunnel_kwargs["ssh_password"] = ssh_password
    else:
        raise ImproperlyConfigured(
            "Provide ALIYUN_SSH_PASSWORD or ALIYUN_SSH_PRIVATE_KEY when SSH tunneling is enabled."
        )

    _DB_TUNNEL = SSHTunnelForwarder((ssh_host, ssh_port), **tunnel_kwargs)
    _DB_TUNNEL.start()
    atexit.register(_close_tunnel)
    return "127.0.0.1", _DB_TUNNEL.local_bind_port


def _close_tunnel():
    global _DB_TUNNEL
    if _DB_TUNNEL is None:
        return
    try:
        _DB_TUNNEL.stop()
    finally:
        _DB_TUNNEL = None


def _require_env(env_get, name: str) -> str:
    value = env_get(name)
    if value in (None, ""):
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return value
