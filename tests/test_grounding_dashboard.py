from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_grounding_dashboard_tracks_and_denominators():
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "dashboard.py"), default_timeout=10
    ).run()
    app.sidebar.selectbox[0].select("视觉贡献干预 v3").run()
    assert not app.exception
    assert any("54.7%" in m.value for m in app.metric)
    next(w for w in app.selectbox if w.label == "数据划分").select("dev").run()
    assert not app.exception
