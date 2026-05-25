import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SERVICE_DIR = Path(__file__).resolve().parent
SHARED_DIR = Path(os.environ.get("AI_SERVICE_TEST_DIR", str(SERVICE_DIR / "test"))).resolve()
LOCAL_INFER_ENTRYPOINT = Path(
    os.environ.get("AI_SERVICE_ENTRYPOINT", str(SERVICE_DIR / "local_infer.py"))
).resolve()
AI_SERVICE_PYTHON = os.environ.get("AI_SERVICE_PYTHON", sys.executable)
AI_REMOTE_INFER_TOKEN = os.environ.get("AI_REMOTE_INFER_TOKEN", "").strip()
AI_REMOTE_INFER_HOST = os.environ.get("AI_REMOTE_INFER_HOST", "127.0.0.1")
AI_REMOTE_INFER_PORT = int(os.environ.get("AI_REMOTE_INFER_PORT", "18080"))
AI_REMOTE_INFER_MAX_CONCURRENCY = max(
    1,
    int(os.environ.get("AI_REMOTE_INFER_MAX_CONCURRENCY", "1") or "1"),
)
AI_SERVICE_INFER_TIMEOUT = int(os.environ.get("AI_SERVICE_INFER_TIMEOUT", "1800"))
AI_REMOTE_INFER_TMP_DIR = Path(
    os.environ.get("AI_SERVICE_TMP_DIR", str(Path.home() / ".codex" / "memories" / ".tmp_ai_service"))
)
AI_REMOTE_INFER_TORCH_HOME = Path(
    os.environ.get("AI_SERVICE_TORCH_HOME", str(Path.home() / ".codex" / "memories" / ".torch_cache"))
)

_REQUEST_LIMITER = threading.Semaphore(AI_REMOTE_INFER_MAX_CONCURRENCY)


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


def _json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _create_request_dir():
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="request_", dir=str(SHARED_DIR)))


def _run_local_infer_with_payload(img_zip_bytes, data_json_bytes):
    request_dir = _create_request_dir()
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    AI_REMOTE_INFER_TMP_DIR.mkdir(parents=True, exist_ok=True)
    AI_REMOTE_INFER_TORCH_HOME.mkdir(parents=True, exist_ok=True)

    try:
        zip_path = request_dir / "img.zip"
        data_path = request_dir / "data.json"
        zip_path.write_bytes(img_zip_bytes)
        data_path.write_bytes(data_json_bytes)

        env = os.environ.copy()
        env["AI_SERVICE_TEST_DIR"] = str(request_dir)
        env["AI_SERVICE_CACHE_ROOT"] = str(request_dir / "cache")
        env["TMP"] = str(AI_REMOTE_INFER_TMP_DIR)
        env["TEMP"] = str(AI_REMOTE_INFER_TMP_DIR)
        env["TMPDIR"] = str(AI_REMOTE_INFER_TMP_DIR)
        env["TORCH_HOME"] = str(AI_REMOTE_INFER_TORCH_HOME)

        try:
            process = subprocess.run(
                [AI_SERVICE_PYTHON, str(LOCAL_INFER_ENTRYPOINT)],
                cwd=str(SERVICE_DIR),
                capture_output=True,
                env=env,
                timeout=AI_SERVICE_INFER_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Local infer subprocess timed out after {AI_SERVICE_INFER_TIMEOUT} seconds."
            ) from exc
        stdout_text = _decode_output(process.stdout)
        stderr_text = _decode_output(process.stderr)
        if process.returncode != 0:
            err = stderr_text.strip() or stdout_text.strip()
            raise RuntimeError(
                f"Local infer subprocess exited with code {process.returncode}. "
                + (f"Error output: {err}" if err else "No error output was captured.")
            )

        lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
        try:
            index = next(i for i, line in enumerate(lines) if "start results" in line.lower())
            return lines[index + 1]
        except (StopIteration, IndexError) as exc:
            first_line = lines[0] if lines else "(no output)"
            raise RuntimeError(
                "Local infer output did not contain the expected 'start results' marker. "
                f"First line received: {first_line!r}"
            ) from exc
    finally:
        shutil.rmtree(request_dir, ignore_errors=True)


class GPUInferRequestHandler(BaseHTTPRequestHandler):
    server_version = "GPUInferService/1.0"

    def do_GET(self):
        if self.path == "/health":
            _json_response(
                self,
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service_dir": str(SERVICE_DIR),
                    "entrypoint": str(LOCAL_INFER_ENTRYPOINT),
                },
            )
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/infer":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        if AI_REMOTE_INFER_TOKEN:
            auth_header = self.headers.get("Authorization", "")
            expected = f"Bearer {AI_REMOTE_INFER_TOKEN}"
            if auth_header != expected:
                _json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "empty_body"})
            return

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        img_zip_base64 = payload.get("img_zip_base64")
        data_json_base64 = payload.get("data_json_base64")
        if not img_zip_base64 or not data_json_base64:
            _json_response(
                self,
                HTTPStatus.BAD_REQUEST,
                {"error": "img_zip_base64 and data_json_base64 are required"},
            )
            return

        try:
            img_zip_bytes = base64.b64decode(img_zip_base64)
            data_json_bytes = base64.b64decode(data_json_base64)
        except Exception:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid_base64"})
            return

        try:
            with _REQUEST_LIMITER:
                result_base64 = _run_local_infer_with_payload(img_zip_bytes, data_json_bytes)
        except Exception as exc:
            _json_response(
                self,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "inference_failed", "detail": str(exc)},
            )
            return

        _json_response(self, HTTPStatus.OK, {"result_base64": result_base64})

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer((AI_REMOTE_INFER_HOST, AI_REMOTE_INFER_PORT), GPUInferRequestHandler)
    print(
        json.dumps(
            {
                "status": "starting",
                "host": AI_REMOTE_INFER_HOST,
                "port": AI_REMOTE_INFER_PORT,
                "max_concurrency": AI_REMOTE_INFER_MAX_CONCURRENCY,
                "service_dir": str(SERVICE_DIR),
                "entrypoint": str(LOCAL_INFER_ENTRYPOINT),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
