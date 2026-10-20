"""Read local edition metadata. Never returns document text or contacts a provider."""
import importlib
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def _norm(value):
    text = str(value or "").lower()
    for a, b in {"ß": "ss", "æ": "ae", "œ": "oe", "ø": "o", "ł": "l", "&": " and "}.items():
        text = text.replace(a, b)
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def _language(value):
    n = _norm(value)
    groups = {"english": "en eng", "german": "de deu ger deutsch", "french": "fr fra fre", "italian": "it ita", "spanish": "es spa", "latin": "la lat", "greek": "el ell grc", "russian": "ru rus", "portuguese": "pt por", "dutch": "nl nld dut"}
    return next((k for k, v in groups.items() if n == k or n in v.split()), n)


def _surname(name):
    n = str(name or "")
    tokens = _norm(n.split(",")[0] if "," in n else n).split()
    tokens = [t for t in tokens if t not in {"jr", "sr", "ii", "iii"}]
    return " ".join(tokens) if "," in n else tokens[-1] if tokens else ""


def _volume(title):
    m = re.search(r"\b(?:vol(?:ume)?|v|bd|band|tome?|tomo|t|part|pt|book|bk|teil|livre)\.?\s*([0-9]+|[ivxlc]+|one|two|three|four|five|six|seven|eight|nine|ten)\b", title or "", re.I)
    if not m:
        return None
    v = m[1].lower()
    if v.isdigit():
        return int(v)
    words = "one two three four five six seven eight nine ten".split()
    if v in words:
        return words.index(v) + 1
    values = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
    return sum(values[c] * (-1 if i + 1 < len(v) and values[v[i + 1]] > values[c] else 1) for i, c in enumerate(v))


def _epub(file):
    dc = "{http://purl.org/dc/elements/1.1/}"
    opf = "{http://www.idpf.org/2007/opf}"
    with zipfile.ZipFile(file) as z:
        def xml(name):
            if z.getinfo(name).file_size > 1024 * 1024:
                raise ValueError("metadata too large")
            return ET.fromstring(z.read(name))
        container = xml("META-INF/container.xml")
        rootfile = next(e for e in container.iter() if e.tag.endswith("}rootfile"))
        package = xml(rootfile.attrib["full-path"])
        metadata = next(e for e in package.iter() if e.tag == opf + "metadata")
        found = {}
        for key, tag in [("title", "title"), ("publisher", "publisher"), ("date", "date"), ("language", "language")]:
            node = metadata.find(dc + tag)
            if node is not None and node.text:
                found[key] = node.text.strip()
        roles = {e.attrib.get("refines", "").lstrip("#"): (e.text or "").strip() for e in metadata if e.attrib.get("property") == "role"}
        creators = []
        for e in metadata:
            if e.tag in {dc + "creator", dc + "contributor"} and e.text:
                creators.append({"name": e.text.strip(), "role": e.attrib.get(opf + "role") or roles.get(e.attrib.get("id")) or ("aut" if e.tag == dc + "creator" else "unknown")})
            if e.tag == dc + "identifier" and e.text and ("isbn" in str(e.attrib).lower() or "isbn" in e.text.lower() or re.fullmatch(r"[\d-]{10,17}", e.text.strip())):
                found["isbn"] = e.text.strip()
        if creators:
            found["creators"] = creators
        return found, ""


def _pdf(file):
    try:
        reader_module = importlib.import_module("pypdf")
    except ImportError:
        return {}, "", "no_pdf_reader"
    try:
        reader = reader_module.PdfReader(str(file))
        meta = reader.metadata or {}
        found = {}
        for key, tag in [("title", "/Title"), ("publisher", "/Publisher"), ("date", "/CreationDate")]:
            if meta.get(tag):
                found[key] = str(meta[tag])
        if meta.get("/Author"):
            found["creators"] = [{"name": str(meta["/Author"]), "role": "aut"}]
        chunks = []
        remaining = 20000
        for i in range(min(4, len(reader.pages))):
            chunk = (reader.pages[i].extract_text() or "")[:remaining]
            chunks.append(chunk)
            remaining -= len(chunk)
            if not remaining:
                break
        text = "\n".join(chunks)
        # Subject contributes edition evidence in memory only.
        evidence = (str(meta.get("/Subject", "")) + "\n" + text)[:20000]
        return found, evidence, None if text.strip() else "scan"
    except Exception:
        return {}, "", "scan"


def inspect_file(path, request=None, language=None, volume=None):
    """Compare affirmative local evidence; missing fields never contradict a request."""
    request = request or {}
    file = Path(path)
    try:
        if file.suffix.lower() == ".epub":
            found, text = _epub(file)
            unreadable = None
        elif file.suffix.lower() == ".pdf":
            found, text, unreadable = _pdf(file)
        else:
            return {"status": "unverified", "reason": "format", "found": {}, "checks": {}}
    except (OSError, ValueError, KeyError, StopIteration, zipfile.BadZipFile, ET.ParseError):
        return {"status": "unverified", "reason": "unreadable", "found": {}, "checks": {}}
    checks = {}
    title = found.get("title")
    creators = found.get("creators", [])
    # The worker resolves orientation before calling this module.
    req_title, req_author = request.get("title", ""), request.get("author", "")
    tokens = lambda s: _norm(re.split(r":| — | – |\(", s)[0]).split()
    a, b = tokens(req_title), tokens(title or "")
    score = 2 * len(set(a) & set(b)) / (len(a) + len(b)) if a or b else 0
    surname = _surname(req_author)
    author_match = bool(surname and surname in _norm(" ".join(c["name"] for c in creators) + " " + text).split())
    checks["work"] = "match" if score >= .5 or author_match else "contradict" if title or creators else "absent"
    wanted_language = request.get("language") or language
    if wanted_language:
        checks["language"] = "match" if found.get("language") and _language(found["language"]) == _language(wanted_language) else "contradict" if found.get("language") else "absent"
    actual_volume = _volume(title or "")
    wanted_volume = request.get("volume", volume)
    if wanted_volume is not None or actual_volume is not None:
        checks["volume"] = "absent" if actual_volume is None else "match" if actual_volume == wanted_volume else "contradict"
    if request.get("mode") == "exact":
        for field, role, pattern in [("translator", "trl", r"translated by\s+([^.;\n]+)"), ("editor", "edt", r"(?:edited by|ed\.)\s+([^.;\n]+)")]:
            if request.get(field):
                people = [c["name"] for c in creators if c["role"] == role]
                people += re.findall(pattern, text, re.I)
                checks[field] = "match" if any(_surname(request[field]) in _norm(p).split() for p in people) else "contradict" if people else "absent"
        if request.get("year"):
            dates = re.findall(r"\b(?:1[5-9]|20)\d{2}\b", str(found.get("date", "")) + " " + text)
            checks["year"] = "match" if any(abs(int(y) - int(request["year"])) <= 1 for y in dates) else "contradict" if dates else "absent"
        if request.get("formats"):
            checks["formats"] = "match" if file.suffix.lower().lstrip(".") in request["formats"] else "contradict"
    status = "mismatch" if "contradict" in checks.values() else "unverified" if unreadable or "absent" in checks.values() else "verified"
    return {"status": status, **({"reason": unreadable or "metadata_absent"} if status == "unverified" else {}), "found": found, "checks": checks}
