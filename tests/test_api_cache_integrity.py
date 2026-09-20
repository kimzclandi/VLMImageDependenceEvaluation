import json

import httpx
import pytest

from flywheel.adapters import APIAdapter, ModelInput


@pytest.fixture
def adapter(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"answer":"2"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )

    a = APIAdapter(
        "m",
        "https://provider.invalid/v1",
        "placeholder",
        tmp_path,
        "p",
        transport=httpx.MockTransport(handler),
    )
    yield a, calls, tmp_path
    a.close()


def item(q="count?"):
    return ModelInput(q, b"fixture", {}, {"kind": "count"})


@pytest.mark.parametrize(
    "bad", [{}, {"raw_output": "wrong"}, {"error": "http_500"}, {"raw_output": 23}, []]
)
def test_malformed_or_legacy_cache_is_a_miss(adapter, bad):
    a, calls, root = adapter
    a.predict(item())
    path = next(root.glob("*.json"))
    path.write_text(json.dumps(bad))
    result = a.predict(item())
    assert not result.cache_hit and result.raw_output == '{"answer":"2"}' and len(calls) == 2


def test_copied_cache_cannot_answer_another_question(adapter):
    a, calls, root = adapter
    a.predict(item("A"))
    first = next(root.glob("*.json"))
    a.predict(item("B"))
    second = next(p for p in root.glob("*.json") if p != first)
    second.write_bytes(first.read_bytes())
    result = a.predict(item("B"))
    assert not result.cache_hit and len(calls) == 3


@pytest.mark.parametrize(
    "usage",
    [
        {"prompt_tokens": -1, "completion_tokens": 2},
        {"prompt_tokens": True, "completion_tokens": 2},
        {"prompt_tokens": float("nan"), "completion_tokens": 2},
        [],
    ],
)
def test_bad_usage_is_not_persisted(tmp_path, usage):
    a = APIAdapter(
        "m",
        "https://provider.invalid",
        "placeholder",
        tmp_path,
        "p",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                content=json.dumps(
                    {"choices": [{"message": {"content": "ok"}}], "usage": usage}
                ).encode(),
            )
        ),
    )
    try:
        assert a.predict(item()).error == "invalid_response"
        assert not list(tmp_path.glob("*.json"))
    finally:
        a.close()


@pytest.mark.parametrize(
    "kwargs", [{"timeout": float("nan")}, {"retries": True}, {"input_price": float("inf")}]
)
def test_nonfinite_configuration_is_rejected(tmp_path, kwargs):
    with pytest.raises(ValueError):
        APIAdapter("m", "https://provider.invalid", "placeholder", tmp_path, "p", **kwargs)


def test_changed_cache_payload_is_a_miss(adapter):
    a, calls, root = adapter
    a.predict(item())
    path = next(root.glob("*.json"))
    saved = json.loads(path.read_text())
    saved["reply"]["raw_output"] = "changed"
    path.write_text(json.dumps(saved))
    assert not a.predict(item()).cache_hit and len(calls) == 2


def test_failed_atomic_replace_preserves_cache(adapter, monkeypatch):
    a, _, root = adapter
    reply = a.predict(item())
    path = next(root.glob("*.json"))
    before = path.read_bytes()
    saved = json.loads(before)

    def fail(*args):
        raise OSError("injected replacement failure")

    monkeypatch.setattr("flywheel.adapters.os.replace", fail)
    with pytest.raises(OSError, match="injected"):
        a.save_cache(path, saved["key"], reply)
    assert path.read_bytes() == before and not list(root.glob("*.tmp"))
