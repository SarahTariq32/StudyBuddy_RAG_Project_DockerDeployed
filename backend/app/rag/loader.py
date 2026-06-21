from pypdf import PdfReader


def load_single_pdf(path: str) -> str:
    """
    Open a PDF at the given file path, extract text from every page,
    join all pages with a newline, and return as one string.
    """
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)
