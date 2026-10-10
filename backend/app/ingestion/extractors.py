"""File-format text extractors (Module 1).

PDF via PyMuPDF (fitz), DOCX via python-docx, everything else read as
plain UTF-8 text. Each extractor raises ValueError for unreadable files so
the upload endpoint can report a per-file failure instead of failing the batch.
"""
from io import BytesIO


class UnsupportedFileError(ValueError):
    pass


def extract_pdf(data: bytes) -> str:
    import fitz  # PyMuPDF

    pages = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            pages.append(page.get_text("text"))
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError("No extractable text found (scanned/image-only PDFs are not supported yet).")
    return text


def extract_docx(data: bytes) -> str:
    import docx  # python-docx

    document = docx.Document(BytesIO(data))
    lines = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    lines.append(cell.text.strip())
    text = "\n".join(lines).strip()
    if not text:
        raise ValueError("The DOCX file contains no readable paragraphs.")
    return text


def extract_txt(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("The file is empty.")
    return text


EXTENSION_EXTRACTORS = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".txt": extract_txt,
    ".md": extract_txt,
}

# Some browsers send odd MIME types for docx; extension is the source of truth.
ALLOWED_EXTENSIONS = set(EXTENSION_EXTRACTORS)


def extract_text(filename: str, data: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)
    ext = f".{ext[1]}" if len(ext) == 2 else ""
    extractor = EXTENSION_EXTRACTORS.get(ext)
    if extractor is None:
        raise UnsupportedFileError(f"Unsupported file type '{ext or filename}'. Allowed: PDF, DOCX, TXT.")
    return extractor(data)
