"""capabilities/image/local_inference_client"""
import base64
import os
import pickle
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.services.capabilities.image import local_inference_client as client

pytestmark = pytest.mark.unit


# ---------- _decode_output ----------

def test_decode_output_returns_empty_string_for_none():
    assert client._decode_output(None) == ""


def test_decode_output_passes_through_string():
    assert client._decode_output("already-text") == "already-text"


def test_decode_output_decodes_utf8_bytes():
    assert client._decode_output("中文 UTF-8".encode("utf-8")) == "中文 UTF-8"


def test_decode_output_falls_back_to_gbk():
    text = client._decode_output("你好".encode("gbk"))
    assert text == "你好"


def test_decode_output_does_not_raise_on_undecodable_bytes():
    assert client._decode_output(b"\xff\xfe\xfd") == ""


# ---------- _discover_ai_service_dir ----------

def test_discover_uses_env_var_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_DIR", str(tmp_path))
    assert client._discover_ai_service_dir() == tmp_path


def test_discover_falls_back_to_default_candidates_when_env_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("AI_SERVICE_DIR", raising=False)
    fake_dir = tmp_path / "fake-ai-service"
    fake_dir.mkdir()
    with patch.object(client, "DEFAULT_AI_SERVICE_DIR_CANDIDATES", [fake_dir]):
        assert client._discover_ai_service_dir() == fake_dir


def test_discover_raises_when_no_candidate_exists(monkeypatch, tmp_path):
    monkeypatch.delenv("AI_SERVICE_DIR", raising=False)
    with patch.object(client, "DEFAULT_AI_SERVICE_DIR_CANDIDATES", [tmp_path / "missing"]):
        with pytest.raises(FileNotFoundError, match="AI_SERVICE_DIR"):
            client._discover_ai_service_dir()


# ---------- _prepare_inputs ----------

def test_prepare_inputs_copies_zip_into_test_dir(tmp_path, monkeypatch):
    src_zip = tmp_path / "src.zip"
    with zipfile.ZipFile(src_zip, "w") as zf:
        zf.writestr("dummy.png", b"x")
    src_json = tmp_path / "src.json"
    src_json.write_text('{"k": 1}', encoding="utf-8")
    test_dir = tmp_path / "test-dir"
    monkeypatch.setattr(client, "AI_SERVICE_TEST_DIR", test_dir)

    zip_path, json_path = client._prepare_inputs(str(src_zip), str(src_json))
    assert zip_path == test_dir / "img.zip"
    assert json_path == test_dir / "data.json"
    assert zip_path.exists()
    assert json_path.exists()


def test_prepare_inputs_zips_non_zip_source(tmp_path, monkeypatch):
    src_png = tmp_path / "image.png"
    src_png.write_bytes(b"fake-png-bytes")
    src_json = tmp_path / "data.json"
    src_json.write_text("{}", encoding="utf-8")
    test_dir = tmp_path / "test-dir"
    monkeypatch.setattr(client, "AI_SERVICE_TEST_DIR", test_dir)

    zip_path, _ = client._prepare_inputs(str(src_png), str(src_json))
    with zipfile.ZipFile(zip_path) as zf:
        assert "image.png" in zf.namelist()


# ---------- _run_local_inference ----------

@patch.object(client, "AI_SERVICE_DIR", Path(__file__).resolve())
@patch("core.services.capabilities.image.local_inference_client.subprocess.run")
def test_run_local_inference_decodes_pickled_payload(mock_run, tmp_path, monkeypatch):
    monkeypatch.setattr(client, "AI_SERVICE_TEST_DIR", tmp_path / "test")
    monkeypatch.setattr(client, "AI_SERVICE_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(client, "AI_SERVICE_TORCH_HOME", tmp_path / "torch")

    payload = [("llm", []), ("ela", [])]
    encoded = base64.b64encode(pickle.dumps(payload)).decode("utf-8")
    mock_run.return_value = SimpleNamespace(
        returncode=0,
        stdout=f"booting\nstart results\n{encoded}\n".encode("utf-8"),
        stderr=b"",
    )

    result = client._run_local_inference()
    assert result == payload


@patch.object(client, "AI_SERVICE_DIR", Path(__file__).resolve())
@patch("core.services.capabilities.image.local_inference_client.subprocess.run")
def test_run_local_inference_raises_on_nonzero_exit_code(mock_run, tmp_path, monkeypatch):
    monkeypatch.setattr(client, "AI_SERVICE_TEST_DIR", tmp_path / "test")
    monkeypatch.setattr(client, "AI_SERVICE_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(client, "AI_SERVICE_TORCH_HOME", tmp_path / "torch")

    mock_run.return_value = SimpleNamespace(returncode=1, stdout=b"", stderr=b"ouch")
    with pytest.raises(RuntimeError, match="exited with code 1"):
        client._run_local_inference()


@patch.object(client, "AI_SERVICE_DIR", Path(__file__).resolve())
@patch("core.services.capabilities.image.local_inference_client.subprocess.run")
def test_run_local_inference_raises_when_marker_missing(mock_run, tmp_path, monkeypatch):
    monkeypatch.setattr(client, "AI_SERVICE_TEST_DIR", tmp_path / "test")
    monkeypatch.setattr(client, "AI_SERVICE_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(client, "AI_SERVICE_TORCH_HOME", tmp_path / "torch")

    mock_run.return_value = SimpleNamespace(returncode=0, stdout=b"no marker here", stderr=b"")
    with pytest.raises(RuntimeError, match="start results"):
        client._run_local_inference()
