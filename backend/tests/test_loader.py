from unittest.mock import MagicMock

from app.rag import loader


def test_load_pdf(mocker):
    page = MagicMock()

    page.extract_text.return_value = "Hello"

    reader = MagicMock()

    reader.pages = [page]

    mocker.patch(
        "app.rag.loader.PdfReader",
        return_value=reader,
    )

    text = loader.load_single_pdf("dummy.pdf")

    assert text == "Hello"


def test_empty_page(mocker):
    page = MagicMock()

    page.extract_text.return_value = ""

    reader = MagicMock()

    reader.pages = [page]

    mocker.patch(
        "app.rag.loader.PdfReader",
        return_value=reader,
    )

    text = loader.load_single_pdf("dummy.pdf")

    assert text == ""