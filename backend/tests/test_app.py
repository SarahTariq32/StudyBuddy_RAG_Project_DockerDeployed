from app.main import app


def test_app_created():
    assert app is not None


def test_app_title():
    assert app.title == "RAG Backend"