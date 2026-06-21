from fastapi import UploadFile, HTTPException
from pypdf import PdfReader
import io

MAX_BYTES = 1_000_000
_SUPPORTED_TYPES = {"application/pdf", "text/plain", "text/markdown"}
_SUPPORTED_EXTS = {".pdf", ".txt", ".md"}


async def extract_cv_text(file: UploadFile) -> str:
    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(400, "CV file is empty")

    content_type = file.content_type or ""
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    is_pdf = ext == ".pdf" or (not ext and "pdf" in content_type)
    is_text = ext in {".txt", ".md"} or (not ext and "text" in content_type)

    if not is_pdf and not is_text:
        raise HTTPException(415, f"Unsupported file type '{ext or content_type}'. Upload PDF or plain text.")

    if is_pdf:
        return _parse_pdf(raw)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    return _cap(text)


def _parse_pdf(raw: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return _cap("\n".join(pages))
    except Exception as e:
        raise HTTPException(422, f"PDF parse failed: {e}")


def _cap(text: str) -> str:
    text = text.strip()
    if not text:
        raise HTTPException(422, "CV text is empty after extraction")
    return text[:MAX_BYTES]
