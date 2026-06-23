from pypdf import PdfReader


def load_single_pdf(path: str, max_pages: int | None = None) -> str:
    """
    Open a PDF at the given file path, extract text from every page,
    join all pages with a newline, and return as one string.
    """
    reader = PdfReader(path)
    pages_source = reader.pages if max_pages is None else reader.pages[:max_pages]
    pages = [page.extract_text() or "" for page in pages_source]
    return "\n".join(pages)
