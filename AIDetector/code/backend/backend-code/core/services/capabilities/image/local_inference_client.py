import base64
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

import requests


CODE_DIR = Path(__file__).resolve().parents[6]
WORKSPACE_ROOT = CODE_DIR.parents[1]


def _build_default_ai_service_dir_candidates():
    candidates = [
        CODE_DIR / "ai-service" / "ai-service-code",
        WORKSPACE_ROOT / "AIDetector" / "code" / "ai-service" / "ai-service-code",
        WORKSPACE_ROOT / "ai-forensics" / "code" / "ai-service" / "ai-service-code",
    ]
    deduped = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


DEFAULT_AI_SERVICE_DIR_CANDIDATES = _build_default_ai_service_dir_candidates()
DEFAULT_SHARED_ROOT = Path.home() / ".codex" / "memories"
AI_SERVICE_DIR = None
AI_SERVICE_ENTRYPOINT = None


def _discover_ai_service_dir():
    configured = os.environ.get("AI_SERVICE_DIR")
    if configured:
        configured_path = Path(configured)
        if configured_path.exists():
            return configured_path
    for candidate in DEFAULT_AI_SERVICE_DIR_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Unable to locate the local AI service directory. "
        "Set AI_SERVICE_DIR or ensure ai-service/ai-service-code exists in the repository."
    )


AI_SERVICE_TEST_DIR = Path(
    os.environ.get("AI_SERVICE_TEST_DIR", str(DEFAULT_SHARED_ROOT / ".ai_service_io"))
)
AI_SERVICE_PYTHON = os.environ.get("AI_SERVICE_PYTHON", sys.executable)
AI_SERVICE_TMP_DIR = Path(
    os.environ.get("AI_SERVICE_TMP_DIR", str(DEFAULT_SHARED_ROOT / ".tmp_ai_service"))
)
AI_SERVICE_TORCH_HOME = Path(
    os.environ.get("AI_SERVICE_TORCH_HOME", str(DEFAULT_SHARED_ROOT / ".torch_cache"))
)
AI_REMOTE_INFER_URL = os.environ.get("AI_REMOTE_INFER_URL", "").strip()
AI_REMOTE_INFER_TIMEOUT = int(os.environ.get("AI_REMOTE_INFER_TIMEOUT", "1800"))
AI_REMOTE_INFER_TOKEN = os.environ.get("AI_REMOTE_INFER_TOKEN", "").strip()
AI_SERVICE_INFER_TIMEOUT = int(os.environ.get("AI_SERVICE_INFER_TIMEOUT", "1800"))
AI_SERVICE_SERIALIZE_LOCAL_INFER = os.environ.get("AI_SERVICE_SERIALIZE_LOCAL_INFER", "1").lower() not in {
    "0",
    "false",
    "no",
}
AI_SERVICE_LOCK_FILE = Path(
    os.environ.get("AI_SERVICE_LOCK_FILE", str(DEFAULT_SHARED_ROOT / ".ai_service_infer.lock"))
)

_LOCAL_INFER_THREAD_LOCK = threading.Lock()


def _create_request_dir():
    AI_SERVICE_TEST_DIR.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="request_", dir=str(AI_SERVICE_TEST_DIR)))


def _prepare_inputs(local_path, json_path, request_dir=None):
    if request_dir is None:
        request_dir = AI_SERVICE_TEST_DIR
    request_dir = Path(request_dir)
    request_dir.mkdir(parents=True, exist_ok=True)
    source_zip = Path(local_path)
    source_json = Path(json_path)
    target_zip = request_dir / "img.zip"
    target_json = request_dir / "data.json"

    if source_json.resolve() != target_json.resolve():
        shutil.copy2(source_json, target_json)

    if source_zip.suffix.lower() == ".zip":
        if source_zip.resolve() != target_zip.resolve():
            shutil.copy2(source_zip, target_zip)
    else:
        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(source_zip, arcname=source_zip.name)

    return target_zip, target_json


def _decode_output(output):
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    for encoding in ("utf-8", "gbk", "utf-8-sig"):
        try:
            return output.decode(encoding)
        except UnicodeDecodeError:
            continue
    return output.decode("utf-8", errors="ignore")


@contextlib.contextmanager
def _serialized_local_inference():
    if not AI_SERVICE_SERIALIZE_LOCAL_INFER:
        yield
        return

    with _LOCAL_INFER_THREAD_LOCK:
        try:
            AI_SERVICE_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
            lock_handle = AI_SERVICE_LOCK_FILE.open("a+")
        except OSError:
            yield
            return

        with lock_handle:
            try:
                import fcntl

                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            except (ImportError, OSError):
                fcntl = None
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _load_remote_infer_config():
    url = (os.environ.get("AI_REMOTE_INFER_URL", "") or AI_REMOTE_INFER_URL).strip()
    token = (os.environ.get("AI_REMOTE_INFER_TOKEN", "") or AI_REMOTE_INFER_TOKEN).strip()
    timeout_raw = os.environ.get("AI_REMOTE_INFER_TIMEOUT")
    if timeout_raw in (None, ""):
        timeout = AI_REMOTE_INFER_TIMEOUT
    else:
        timeout = int(timeout_raw)
    return {"url": url, "token": token, "timeout": timeout}


def _run_remote_inference(request_dir=None):
    config = _load_remote_infer_config()
    infer_url = config["url"]
    if not infer_url:
        raise RuntimeError("AI_REMOTE_INFER_URL is not configured.")

    io_dir = Path(request_dir) if request_dir is not None else AI_SERVICE_TEST_DIR
    zip_path = io_dir / "img.zip"
    data_path = io_dir / "data.json"
    if not zip_path.exists():
        raise FileNotFoundError(f"Remote inference input zip not found: {zip_path}")
    if not data_path.exists():
        raise FileNotFoundError(f"Remote inference input json not found: {data_path}")

    headers = {}
    if config["token"]:
        headers["Authorization"] = f"Bearer {config['token']}"

    request_payload = {
        "img_zip_base64": base64.b64encode(zip_path.read_bytes()).decode("utf-8"),
        "data_json_base64": base64.b64encode(data_path.read_bytes()).decode("utf-8"),
    }
    headers["Content-Type"] = "application/json"

    response = requests.post(
        infer_url,
        headers=headers,
        json=request_payload,
        timeout=config["timeout"],
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body_preview = response.text[:500] if response.text else ""
        raise RuntimeError(
            f"Remote AI inference request failed with HTTP {response.status_code}. "
            f"Response: {body_preview}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        body_preview = response.text[:500] if response.text else ""
        raise RuntimeError(
            "Remote AI inference response was not valid JSON. "
            f"Response: {body_preview}"
        ) from exc

    encoded_payload = payload.get("result_base64")
    if not encoded_payload:
        raise RuntimeError("Remote AI inference response did not contain result_base64.")

    import pickle

    return pickle.loads(base64.b64decode(encoded_payload))


def _run_local_inference(request_dir=None):
    remote_config = _load_remote_infer_config()
    if remote_config["url"]:
        return _run_remote_inference(request_dir=request_dir)

    ai_service_dir = AI_SERVICE_DIR or _discover_ai_service_dir()
    ai_service_entrypoint = Path(
        AI_SERVICE_ENTRYPOINT
        or os.environ.get("AI_SERVICE_ENTRYPOINT", str(ai_service_dir / "local_infer.py"))
    )

    io_dir = Path(request_dir) if request_dir is not None else AI_SERVICE_TEST_DIR
    io_dir.mkdir(parents=True, exist_ok=True)
    AI_SERVICE_TMP_DIR.mkdir(parents=True, exist_ok=True)
    AI_SERVICE_TORCH_HOME.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["AI_SERVICE_TEST_DIR"] = str(io_dir)
    env["AI_SERVICE_CACHE_ROOT"] = (io_dir / "cache").as_posix()
    env["TMP"] = str(AI_SERVICE_TMP_DIR)
    env["TEMP"] = str(AI_SERVICE_TMP_DIR)
    env["TMPDIR"] = str(AI_SERVICE_TMP_DIR)
    env["TORCH_HOME"] = str(AI_SERVICE_TORCH_HOME)

    try:
        with _serialized_local_inference():
            process = subprocess.run(
                [AI_SERVICE_PYTHON, str(ai_service_entrypoint)],
                cwd=str(ai_service_dir),
                capture_output=True,
                env=env,
                timeout=AI_SERVICE_INFER_TIMEOUT,
            )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Local AI service subprocess timed out after {AI_SERVICE_INFER_TIMEOUT} seconds."
        ) from exc
    stdout_text = _decode_output(process.stdout)
    stderr_text = _decode_output(process.stderr)
    if process.returncode != 0:
        err = stderr_text.strip() or stdout_text.strip()
        raise RuntimeError(
            f"Local AI service subprocess exited with code {process.returncode}. "
            + (f"Error output: {err}" if err else "No error output was captured.")
        )

    lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
    try:
        index = next(i for i, line in enumerate(lines) if "start results" in line.lower())
        payload = lines[index + 1]
    except (StopIteration, IndexError) as exc:
        first_line = lines[0] if lines else "(no output)"
        raise RuntimeError(
            f"Local AI service output did not contain the expected 'start results' marker. "
            f"First line received: {first_line!r}"
        ) from exc

    import pickle

    return pickle.loads(base64.b64decode(payload))


def get_result(local_path, json_path):
    request_dir = _create_request_dir()
    try:
        _prepare_inputs(local_path, json_path, request_dir)
        return _run_local_inference(request_dir=request_dir)
    finally:
        shutil.rmtree(request_dir, ignore_errors=True)
