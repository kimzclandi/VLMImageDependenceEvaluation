from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


def test_dashboard_all_pages_and_empty_failure_slice():
    app = AppTest.from_file(Path("dashboard.py").resolve()).run(timeout=30)
    assert not app.exception
    assert "图像" in app.title[0].value
    app.sidebar.selectbox[0].set_value("规则流程演示（历史）").run(timeout=30)
    assert not app.exception
    assert app.metric[0].value == "240"
    for page in ("Failure review", "Data production", "Evidence & configuration"):
        app.sidebar.radio[0].set_value(page).run(timeout=30)
        assert not app.exception, page
    app.sidebar.radio[0].set_value("Failure review").run()
    app.selectbox[0].set_value("v2").run()
    app.selectbox[2].set_value("spatial_relation").run()
    assert not app.exception
    assert "No failed cases" in app.success[0].value


def test_real_model_dashboard():
    app = AppTest.from_file(Path("dashboard.py").resolve()).run(timeout=30)
    app.sidebar.selectbox[0].set_value("真实 VLM 评测").run(timeout=30)
    assert not app.exception
    assert "真实 VLM" in app.title[0].value
    if Path("reports/real_vlm/summary.json").exists():
        next(s for s in app.selectbox if s.label == "评测集").set_value("dev").run(timeout=30)
        assert not app.exception
