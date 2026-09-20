"""Adapters share an input contract; only reference rules receive scene metadata."""

import base64
import copy
import json
import math
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import httpx

from flywheel.data import solve
from flywheel.io import digest, read_json

PROMPT = 'You see a synthetic tabletop. Object IDs are printed below objects. Compare centers. Small objects have radius 18 px; large have radius 27 px. Return only a JSON object {"answer": "..."}. Never include an explanation.'


@dataclass(frozen=True)
class ModelInput:
    """No ground truth. Real API calls receive only question and image bytes."""

    question: str
    image: bytes
    scene: dict
    query: dict


@dataclass
class Reply:
    raw_output: str = ""
    error: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    cache_hit: bool = False
    attempts: int = 1
    provider_model: str | None = None


class Adapter(Protocol):
    name: str
    version: str
    parameters: dict

    def predict(self, item: ModelInput) -> Reply: ...


@dataclass
class ReferenceAdapter:
    """Deliberately limited metadata rules. Neither version trains or reads pixels."""

    version: str = "v1"
    name: str = "metadata-reference-NOT-VLM"
    parameters: dict = field(
        default_factory=lambda: {"deterministic": True, "privileged_metadata": True}
    )

    def __post_init__(self) -> None:
        if self.version not in ("v1", "v2"):
            raise ValueError("Reference version must be v1 or v2")

    def predict(self, item: ModelInput) -> Reply:
        q = copy.deepcopy(item.query)
        if self.version == "v1":
            if q["kind"] == "relation" and q["relation"] in ("above", "below"):
                q["relation"] = "above" if q["relation"] == "below" else "below"
            elif q["kind"] == "exists":
                q["filters"].pop("shape", None)
            elif q["kind"] == "select":
                q["filters"].pop("size", None)
                q.pop("relation", None)
        else:
            # Intentional negative control: the candidate drops small counted objects.
            if q["kind"] == "count":
                q["filters"]["size"] = "large"
        answer = solve(item.scene, q)
        return Reply(
            raw_output=json.dumps({"answer": answer}),
            estimated_cost_usd=0.0,
            provider_model=self.name,
        )


class APIAdapter:
    """Opt-in Chat Completions vision adapter with bounded retries and disk cache.

    Failed requests are never cached. No exception body, URL or credential is logged.
    Token prices are explicit user inputs; unknown price/usage means null, not free.
    """

    name = "openai-compatible"

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        cache: Path,
        prompt_version: str,
        timeout: float = 30.0,
        retries: int = 2,
        input_price: float | None = None,
        output_price: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        parsed = urlparse(base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Use an HTTPS endpoint without credentials, query or fragment")
        if not model or not api_key:
            raise ValueError("Set VLM_MODEL and VLM_API_KEY for optional API mode")
        if (
            type(retries) is not int
            or not 0 <= retries <= 5
            or type(timeout) not in (int, float)
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("Invalid retry or timeout limits")
        if any(
            p is not None and (type(p) not in (int, float) or not math.isfinite(p) or p < 0)
            for p in (input_price, output_price)
        ):
            raise ValueError("Prices must be finite nonnegative numbers")
        self.version = model
        self.cache, self.prompt_version = cache, prompt_version
        self.base_url = base_url.rstrip("/")
        self.retries, self.timeout = retries, timeout
        self.prices = (input_price, output_price)
        self.parameters = {
            "temperature": 0,
            "max_tokens": 100,
            "timeout_seconds": timeout,
            "max_retries": retries,
            "input_usd_per_million": input_price,
            "output_usd_per_million": output_price,
        }
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    @classmethod
    def from_env(cls, cache: Path, prompt_version: str, **kwargs: object) -> "APIAdapter":
        return cls(
            os.environ.get("VLM_MODEL", ""),
            os.environ.get("VLM_BASE_URL", "https://api.openai.com/v1"),
            os.environ.get("VLM_API_KEY", ""),
            cache,
            prompt_version,
            **kwargs,
        )

    def close(self) -> None:
        self.client.close()

    def valid_reply(self, reply: Reply) -> bool:
        counts = (reply.input_tokens, reply.output_tokens)
        cost = reply.estimated_cost_usd
        return (
            isinstance(reply.raw_output, str)
            and reply.error is None
            and reply.cache_hit is False
            and type(reply.attempts) is int
            and 1 <= reply.attempts <= self.retries + 1
            and all(v is None or (type(v) is int and v >= 0) for v in counts)
            and (cost is None or (type(cost) in (int, float) and math.isfinite(cost) and cost >= 0))
            and (reply.provider_model is None or isinstance(reply.provider_model, str))
        )

    @staticmethod
    def save_cache(path: Path, key: str, reply: Reply) -> None:
        value = vars(reply)
        envelope = {"schema": 1, "key": key, "reply_sha256": digest(value), "reply": value}
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=path.parent, prefix=".cache-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(envelope, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)

    def predict(self, item: ModelInput) -> Reply:
        body = {
            "model": self.version,
            "temperature": 0,
            "max_tokens": 100,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": item.question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64,"
                                + base64.b64encode(item.image).decode()
                            },
                        },
                    ],
                },
            ],
        }
        # Endpoint, prompt, model, parameters, prices, image and question all invalidate cache.
        key = digest([self.base_url, body, self.prompt_version, self.parameters])
        cached = self.cache / f"{key}.json"
        if cached.exists():
            try:
                saved = read_json(cached)
                if (
                    not isinstance(saved, dict)
                    or saved.get("schema") != 1
                    or saved.get("key") != key
                    or not isinstance(saved.get("reply"), dict)
                    or set(saved["reply"]) != set(vars(Reply()))
                    or saved.get("reply_sha256") != digest(saved["reply"])
                ):
                    raise ValueError("Cache identity or content mismatch")
                reply = Reply(**saved["reply"])
                if not self.valid_reply(reply):
                    raise ValueError("Invalid cached response metadata")
                reply.cache_hit, reply.attempts, reply.estimated_cost_usd = True, 0, 0.0
                return reply
            except (ValueError, TypeError):
                pass
        for attempt in range(self.retries + 1):
            try:
                response = self.client.post(self.base_url + "/chat/completions", json=body)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.retries:
                        time.sleep(min(0.25 * 2**attempt, 2.0))
                        continue
                if response.status_code >= 300:
                    return Reply(error=f"http_{response.status_code}", attempts=attempt + 1)
                payload = response.json()
                message = payload["choices"][0]["message"]
                if not isinstance(message, dict):
                    return Reply(error="invalid_response", attempts=attempt + 1)
                raw = message.get("content")
                if message.get("refusal"):
                    return Reply(raw_output="", error="refusal", attempts=attempt + 1)
                if not isinstance(raw, str):
                    return Reply(error="invalid_response", attempts=attempt + 1)
                usage = payload.get("usage")
                if usage is None:
                    usage = {}
                if not isinstance(usage, dict):
                    return Reply(error="invalid_response", attempts=attempt + 1)
                inp, out = usage.get("prompt_tokens"), usage.get("completion_tokens")
                if any(v is not None and (type(v) is not int or v < 0) for v in (inp, out)):
                    return Reply(error="invalid_response", attempts=attempt + 1)
                cost = None
                if inp is not None and out is not None and all(p is not None for p in self.prices):
                    cost = (inp * self.prices[0] + out * self.prices[1]) / 1_000_000
                reply = Reply(
                    raw_output=raw,
                    input_tokens=inp,
                    output_tokens=out,
                    estimated_cost_usd=cost,
                    attempts=attempt + 1,
                    provider_model=payload.get("model"),
                )
                if not self.valid_reply(reply):
                    return Reply(error="invalid_response", attempts=attempt + 1)
                self.save_cache(cached, key, reply)
                return reply
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == self.retries:
                    return Reply(error="network_or_timeout", attempts=attempt + 1)
                time.sleep(min(0.25 * 2**attempt, 2.0))
            except (ValueError, KeyError, IndexError, TypeError):
                return Reply(error="invalid_response", attempts=attempt + 1)
        return Reply(error="retry_exhausted")
