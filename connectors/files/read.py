import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from connectors.files.guard import allowed, safe_path, short

MAX_TEXT_CHARS = 12000
MAX_TEXT_FILE_BYTES = 2_000_000
MAX_LISTED = 200
# measuring a whole home folder can take long; stop and say so
DISK_SECONDS = 20

KINDS = {
    "pdf": {".pdf"},
    "document": {".doc", ".docx", ".pages", ".txt", ".md", ".rtf", ".odt"},
    "slides": {".ppt", ".pptx", ".key"},
    "spreadsheet": {".xls", ".xlsx", ".numbers", ".csv"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".heic", ".webp", ".svg"},
    "code": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs", ".ipynb", ".html", ".css"},
}

def kind_of(path):
    if path.is_dir() and path.suffix.lower() not in {".key", ".pages", ".numbers"}:
        return "folder"
    return next((kind for kind, endings in KINDS.items() if path.suffix.lower() in endings), "file")

def card(path):
    # the short facts about one file or folder, for the model and the screen
    info = path.stat()
    return {
        "path": str(path),
        "short": short(path),
        "name": path.name,
        "kind": kind_of(path),
        "size": info.st_size if path.is_file() else None,
        "modified": datetime.fromtimestamp(info.st_mtime).isoformat(timespec="minutes"),
    }

def find(query, folder="~", kind="", max_results=30):
    # Spotlight finds files by name and by what's inside them (PDFs and documents too)
    where = safe_path(folder)
    found = subprocess.run(["mdfind", "-onlyin", str(where), query], capture_output=True, text=True, timeout=15)
    paths = [Path(line) for line in found.stdout.splitlines() if line]
    results = []
    for path in paths:
        if not allowed(path) or not path.exists():
            continue
        if kind and kind_of(path) != kind:
            continue
        results.append(path)
        if len(results) >= max_results * 4:
            break
    # newest first: the file the user means is usually a recent one
    results.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [card(p) for p in results[:max_results]]

def list_folder(folder="~"):
    where = safe_path(folder)
    if not where.is_dir():
        raise NotADirectoryError(f"{short(where)} is a file, not a folder.")
    items = [p for p in where.iterdir() if allowed(p)]
    items.sort(key=lambda p: (kind_of(p) != "folder", p.name.lower()))
    return [card(p) for p in items[:MAX_LISTED]], len(items)

def pdf_text(path):
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages, total = [], 0
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        pages.append(f"[page {number}]\n{text}")
        total += len(text)
        if total > MAX_TEXT_CHARS:
            break
    return "\n\n".join(pages), len(reader.pages)

def docx_text(path):
    from docx import Document

    return "\n".join(p.text for p in Document(str(path)).paragraphs if p.text.strip())

def plain_text(path):
    if path.stat().st_size > MAX_TEXT_FILE_BYTES:
        raise ValueError(f"{path.name} is too big to read as text.")
    data = path.read_bytes()
    if b"\0" in data[:4096]:
        raise ValueError(f"{path.name} isn't a text file, so I can't read it.")
    return data.decode("utf-8", errors="replace")

def read(path):
    real = safe_path(path)
    if real.is_dir():
        raise IsADirectoryError(f"{short(real)} is a folder; list it instead.")
    pages = None
    if real.suffix.lower() == ".pdf":
        text, pages = pdf_text(real)
    elif real.suffix.lower() == ".docx":
        text = docx_text(real)
    else:
        text = plain_text(real)
    cut = len(text) > MAX_TEXT_CHARS
    return card(real) | {"text": text[:MAX_TEXT_CHARS], "cut": cut, "pages": pages}

def info(path):
    real = safe_path(path)
    facts = card(real)
    stat = real.stat()
    facts["created"] = datetime.fromtimestamp(getattr(stat, "st_birthtime", stat.st_ctime)).isoformat(timespec="minutes")
    if real.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        facts["pages"] = len(PdfReader(str(real)).pages)
    return facts

def measure(path):
    # one folder's size in bytes by macOS's du (fast), or None if it takes too long
    try:
        measured = subprocess.run(["du", "-sk", "-I", "Library", str(path)], capture_output=True, text=True, timeout=DISK_SECONDS)
    except subprocess.TimeoutExpired:
        return None
    first = measured.stdout.split("\t", 1)[0]
    return int(first) * 1024 if first.isdigit() else None

def disk_usage(folder="~", top=10):
    # the biggest folders right inside `folder`, and the biggest files anywhere under it
    where = safe_path(folder)
    children = [p for p in where.iterdir() if allowed(p) and p.is_dir() and not p.is_symlink()]
    loose = sum(p.stat().st_size for p in where.iterdir() if allowed(p) and p.is_file())
    # every folder is measured at the same time; sizes are only measured, never read
    with ThreadPoolExecutor(max_workers=8) as pool:
        sizes = list(pool.map(measure, children))
    folders = [{"name": p.name, "size": size} for p, size in zip(children, sizes) if size is not None]
    slow = [p.name for p, size in zip(children, sizes) if size is None]
    folders.sort(key=lambda f: f["size"], reverse=True)

    big = subprocess.run(["mdfind", "-onlyin", str(where), "kMDItemFSSize > 50000000"], capture_output=True, text=True, timeout=15)
    files = [Path(line) for line in big.stdout.splitlines() if line and allowed(line) and Path(line).is_file()]
    files.sort(key=lambda p: p.stat().st_size, reverse=True)
    return {
        "folder": short(where),
        "total": loose + sum(f["size"] for f in folders),
        # folders too big to measure in time are named, not counted
        "too_slow": slow,
        "folders": folders[:top],
        "files": [card(p) for p in files[:top]],
    }
