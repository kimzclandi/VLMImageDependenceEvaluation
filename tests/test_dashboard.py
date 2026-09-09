from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


def test_dashboard_all_pages_and_empty_failure_slice():
    app = AppTest.from_file(Path("dashboard.py").resolve()).run(timeout=30)
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
