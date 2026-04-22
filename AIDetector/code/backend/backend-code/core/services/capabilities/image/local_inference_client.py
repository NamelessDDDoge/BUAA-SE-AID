import base64
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


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


def _prepare_inputs(local_path, json_path):
    AI_SERVICE_TEST_DIR.mkdir(parents=True, exist_ok=True)
    source_zip = Path(local_path)
    source_json = Path(json_path)
    target_zip = AI_SERVICE_TEST_DIR / "img.zip"
    target_json = AI_SERVICE_TEST_DIR / "data.json"

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


def _run_local_inference():
    ai_service_dir = AI_SERVICE_DIR or _discover_ai_service_dir()
    ai_service_entrypoint = Path(
        AI_SERVICE_ENTRYPOINT
        or os.environ.get("AI_SERVICE_ENTRYPOINT", str(ai_service_dir / "local_infer.py"))
    )

    AI_SERVICE_TEST_DIR.mkdir(parents=True, exist_ok=True)
    AI_SERVICE_TMP_DIR.mkdir(parents=True, exist_ok=True)
    AI_SERVICE_TORCH_HOME.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["AI_SERVICE_TEST_DIR"] = str(AI_SERVICE_TEST_DIR)
    env["TMP"] = str(AI_SERVICE_TMP_DIR)
    env["TEMP"] = str(AI_SERVICE_TMP_DIR)
    env["TMPDIR"] = str(AI_SERVICE_TMP_DIR)
    env["TORCH_HOME"] = str(AI_SERVICE_TORCH_HOME)

    process = subprocess.run(
        [AI_SERVICE_PYTHON, str(ai_service_entrypoint)],
        cwd=str(ai_service_dir),
        capture_output=True,
        env=env,
    )
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
    _prepare_inputs(local_path, json_path)
    return _run_local_inference()
