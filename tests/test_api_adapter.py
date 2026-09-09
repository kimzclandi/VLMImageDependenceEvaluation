import json

import httpx
import pytest

from flywheel.adapters import APIAdapter, ModelInput


def item(question="Count red objects"):
    return ModelInput(question, b"synthetic-image", {"private_metadata": True}, {"kind": "count"})


def test_api_payload_cache_usage_and_no_label_leak(tmp_path):
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert "private_metadata" not in request.content.decode()
        assert "ground_truth" not in request.content.decode()
        assert body["messages"][1]["content"][1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )
        return httpx.Response(
            200,
            json={
                "model": "pinned-model-1",
                "choices": [{"message": {"content": '{"answer":"2"}'}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            },
        )

    adapter = APIAdapter(
        "test-model",
        "https://provider.invalid/v1",
        "unit-test-placeholder",
        tmp_path,
        "p1",
        input_price=1,
        output_price=2,
        transport=httpx.MockTransport(handler),
    )
    try:
        first, cached = adapter.predict(item()), adapter.predict(item())
        assert first.estimated_cost_usd == pytest.approx(0.00012)
        assert cached.cache_hit and cached.attempts == 0 and cached.estimated_cost_usd == 0
        assert first.provider_model == "pinned-model-1"
        assert len(calls) == 1
        adapter.predict(item("Another question"))
        assert len(calls) == 2
        adapter.prompt_version = "p2"
        adapter.predict(item())
        assert len(calls) == 3
    finally:
        adapter.close()


@pytest.mark.parametrize("status", [401, 429, 500])
def test_retry_bounds_errors_not_cached(tmp_path, monkeypatch, status):
    monkeypatch.setattr("flywheel.adapters.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(status, text="do-not-persist-sensitive-provider-error")

    adapter = APIAdapter(
        "m",
        "https://provider.invalid/v1",
        "placeholder",
        tmp_path,
        "p1",
        transport=httpx.MockTransport(handler),
    )
    try:
        reply = adapter.predict(item())
        assert reply.error == f"http_{status}"
        assert len(calls) == (1 if status == 401 else 3)
        assert "sensitive" not in str(vars(reply))
        assert not list(tmp_path.glob("*.json"))
    finally:
        adapter.close()


def test_timeout_and_invalid_response(tmp_path, monkeypatch):
    monkeypatch.setattr("flywheel.adapters.time.sleep", lambda _: None)

    def timeout(request):
        raise httpx.ReadTimeout("secret endpoint", request=request)

    adapter = APIAdapter(
        "m",
        "https://provider.invalid",
        "placeholder",
        tmp_path,
        "p",
        transport=httpx.MockTransport(timeout),
    )
    assert adapter.predict(item()).error == "network_or_timeout"
    adapter.close()
    adapter = APIAdapter(
        "m",
        "https://provider.invalid",
        "placeholder",
        tmp_path,
        "p",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})),
    )
    assert adapter.predict(item()).error == "invalid_response"
    adapter.close()


def test_api_rejects_credential_urls(tmp_path):
    with pytest.raises(ValueError, match="HTTPS"):
        APIAdapter("m", "https://user:password@provider.invalid", "placeholder", tmp_path, "p")
