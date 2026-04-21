from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from fake_image_detector.database import build_database_settings


class DatabaseConfigTests(SimpleTestCase):
    def setUp(self):
        self.project_dir = Path("C:/tmp/backend-code")

    def test_local_mode_defaults_to_sqlite(self):
        config = build_database_settings(
            self.project_dir,
            lambda name, default=None: {"DATABASE_MODE": "local"}.get(name, default),
            lambda name, default: default,
            lambda name, default: default,
        )

        self.assertEqual(config["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(config["default"]["NAME"], self.project_dir / "db.sqlite3")

    def test_custom_mode_keeps_legacy_mysql_settings(self):
        values = {
            "DATABASE_MODE": "custom",
            "DB_ENGINE": "django.db.backends.mysql",
            "DB_NAME": "demo",
            "DB_USER": "root",
            "DB_PASSWORD": "secret",
            "DB_HOST": "127.0.0.1",
            "DB_PORT": "3306",
            "DB_CHARSET": "utf8mb4",
        }

        config = build_database_settings(
            self.project_dir,
            lambda name, default=None: values.get(name, default),
            lambda name, default: default,
            lambda name, default: int(values.get(name, default)),
        )

        self.assertEqual(config["default"]["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(config["default"]["NAME"], "demo")
        self.assertEqual(config["default"]["OPTIONS"], {"charset": "utf8mb4"})

    def test_aliyun_mode_requires_remote_values(self):
        with self.assertRaises(ImproperlyConfigured):
            build_database_settings(
                self.project_dir,
                lambda name, default=None: {"DATABASE_MODE": "aliyun_postgres"}.get(name, default),
                lambda name, default: default,
                lambda name, default: default,
            )

    def test_aliyun_mode_builds_postgres_settings_without_tunnel(self):
        values = {
            "DATABASE_MODE": "aliyun_postgres",
            "ALIYUN_DB_HOST": "db.example.internal",
            "ALIYUN_DB_PORT": "5432",
            "ALIYUN_DB_NAME": "detect",
            "ALIYUN_DB_USER": "backend_user",
            "ALIYUN_DB_PASSWORD": "top-secret",
            "ALIYUN_DB_CONNECT_TIMEOUT": "15",
        }

        config = build_database_settings(
            self.project_dir,
            lambda name, default=None: values.get(name, default),
            lambda name, default: default,
            lambda name, default: int(values.get(name, default)),
        )

        self.assertEqual(config["default"]["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["default"]["HOST"], "db.example.internal")
        self.assertEqual(config["default"]["PORT"], "5432")
        self.assertEqual(config["default"]["OPTIONS"], {"connect_timeout": 15})

    @patch("fake_image_detector.database._start_aliyun_db_tunnel", side_effect=RuntimeError("tunnel down"))
    def test_aliyun_mode_falls_back_to_local_sqlite_when_tunnel_start_fails(self, _mock_tunnel):
        values = {
            "DATABASE_MODE": "aliyun_postgres",
            "ALIYUN_DB_USE_SSH_TUNNEL": "true",
            "ALIYUN_DB_HOST": "db.example.internal",
            "ALIYUN_DB_NAME": "detect",
            "ALIYUN_DB_USER": "backend_user",
            "ALIYUN_DB_PASSWORD": "top-secret",
            "DB_ENGINE": "django.db.backends.sqlite3",
            "DB_NAME": "db.sqlite3",
        }

        config = build_database_settings(
            self.project_dir,
            lambda name, default=None: values.get(name, default),
            lambda name, default: str(values.get(name, default)).strip().lower() in {"1", "true", "yes", "on"}
            if name in values
            else default,
            lambda name, default: int(values.get(name, default)),
        )

        self.assertEqual(config["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(config["default"]["NAME"], self.project_dir / "db.sqlite3")

    @patch("fake_image_detector.database._start_aliyun_db_tunnel", side_effect=RuntimeError("tunnel down"))
    def test_aliyun_mode_still_raises_without_fallback_config(self, _mock_tunnel):
        values = {
            "DATABASE_MODE": "aliyun_postgres",
            "ALIYUN_DB_USE_SSH_TUNNEL": "true",
            "ALIYUN_DB_HOST": "db.example.internal",
            "ALIYUN_DB_NAME": "detect",
            "ALIYUN_DB_USER": "backend_user",
            "ALIYUN_DB_PASSWORD": "top-secret",
        }

        with self.assertRaises(RuntimeError):
            build_database_settings(
                self.project_dir,
                lambda name, default=None: values.get(name, default),
                lambda name, default: str(values.get(name, default)).strip().lower() in {"1", "true", "yes", "on"}
                if name in values
                else default,
                lambda name, default: int(values.get(name, default)),
            )
