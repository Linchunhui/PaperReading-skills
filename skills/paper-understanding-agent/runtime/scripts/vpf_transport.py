"""One VPF gateway POST for each local stage attempt."""
from dataclasses import dataclass
from http.client import HTTPException
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid


DEFAULT_ENDPOINT = ""  # Set --vpf-endpoint explicitly; no private gateway is bundled.
DEFAULT_MODEL = "Qwen3.6-35B-A3B-FP8"
MAX_REPLY_BYTES = 32 * 1024**2


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class Exchange:
    elapsed_seconds: float
    stdout: bytes
    stderr: bytes = b""
    returncode: int = 0
    argv: tuple = ()
    pid: int | None = None
    synthetic_response: str | None = None


class VPFTransport:
    def __init__(self, *, endpoint, service_name, caller_name, model, timeout, generation_timeout, max_tokens):
        url = urlsplit(endpoint)
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("VPF endpoint must be an HTTP(S) URL without credentials, query or fragment")
        if not service_name.strip() or not caller_name.strip():
            raise ValueError("VPF service and caller names are required")
        if not 1 <= generation_timeout <= 900 or not 1 <= max_tokens <= 32768:
            raise ValueError("VPF generation timeout must be 1–900 seconds and max_tokens 1–32768")
        self.timeout = timeout
        self.model = model
        self.settings = {"endpoint": endpoint, "service_name": service_name, "caller_name": caller_name,
                         "generation_timeout_s": generation_timeout, "max_tokens": max_tokens}

    def __call__(self, prompt, attempt_dir):
        options = self.settings
        payload = {"request_id": uuid.uuid4().hex, "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": options["max_tokens"], "timeout_s": options["generation_timeout_s"]}
        envelope = {"service_name": options["service_name"], "caller_name": options["caller_name"],
                    "payload": json.dumps(payload, ensure_ascii=False, allow_nan=False)}
        raw_request = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode("utf-8")
        (attempt_dir / "vpf-request.json").write_bytes(raw_request)
        request = Request(options["endpoint"], raw_request, {"Content-Type": "application/json"}, method="POST")
        started = time.monotonic()
        raw_response = b""
        try:
            with build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                raw_response = response.read(MAX_REPLY_BYTES + 1)
            if len(raw_response) > MAX_REPLY_BYTES:
                raise ValueError("VPF response exceeds size limit")
            result = self.result(raw_response)
            if not isinstance(result.get("content"), str):
                raise ValueError("VPF response has no text content")
            (attempt_dir / "final-response.txt").write_text(result["content"], encoding="utf-8")
            return Exchange(time.monotonic() - started, raw_response)
        except HTTPError as exc:
            raw_response = exc.read(MAX_REPLY_BYTES)
            return Exchange(time.monotonic() - started, raw_response, f"VPF HTTP {exc.code}".encode(), 1)
        except (OSError, ValueError, HTTPException) as exc:
            return Exchange(time.monotonic() - started, raw_response, str(exc).encode("utf-8"), 1)

    @staticmethod
    def result(raw):
        reply = json.loads(raw)
        if not isinstance(reply, dict) or reply.get("success") is not True:
            detail = reply.get("error_msg") if isinstance(reply, dict) else None
            if isinstance(detail, str) and detail.strip():
                raise ValueError("VPF gateway rejected the request: " + detail.strip()[:800])
            raise ValueError("VPF gateway rejected the request")
        data = reply.get("data")
        if isinstance(data, str):
            data = json.loads(data)
        result = data.get("result") if isinstance(data, dict) else None
        if isinstance(result, str):
            result = json.loads(result)
        if not isinstance(result, dict):
            raise ValueError("VPF gateway response has no result object")
        return result

    def parse_receipt(self, attempt_dir: Path, raw, content):
        result = self.result(raw)
        request = json.loads((attempt_dir / "vpf-request.json").read_bytes())
        payload = json.loads(request["payload"])
        request_id = payload["request_id"]
        if result.get("request_id") != request_id or result.get("model") != self.model:
            raise ValueError("VPF request ID or served model did not match")
        if result.get("content") != content:
            raise ValueError("Saved VPF content differs from gateway response")
        usage = result.get("usage")
        if not isinstance(usage, dict) or any(
            type(usage.get(key)) is not int or usage[key] < 0
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        ) or usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
            raise ValueError("VPF response has invalid token usage")
        return {"call_id": "vpf:" + request_id, "request_id": request_id, "execution_mode": "vpf",
                "model": result["model"], "usage": usage, "completed_turns": 1,
                "finish_reason": result.get("finish_reason")}
