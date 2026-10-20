"""Local-only edition checks, using generated metadata rather than real books."""
import importlib
import socket
import zipfile
import pytest
from lib.edition_check import inspect_file


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("edition inspection attempted a socket")
    monkeypatch.setattr(socket, "socket", refused)


def epub(tmp_path, version=2, title="Being and Time", language="en", translator="Joan Stambaugh"):
    file = tmp_path / f"edition-{version}.epub"
    with zipfile.ZipFile(file, "w") as z:
        z.writestr("META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/book.opf"/></rootfiles></container>')
        roles = ' opf:role="{}"' if version == 2 else ' id="{}"'
        creators = '<dc:creator' + roles.format("aut" if version == 2 else "author") + '>Martin Heidegger</dc:creator>'
        creators += '<dc:contributor' + roles.format("trl" if version == 2 else "translator") + f'>{translator}</dc:contributor>'
        creators += '<dc:contributor' + roles.format("edt" if version == 2 else "editor") + '>John Editor</dc:contributor>'
        if version == 3:
            creators += '<meta refines="#author" property="role">aut</meta><meta refines="#translator" property="role">trl</meta><meta refines="#editor" property="role">edt</meta>'
        z.writestr("OEBPS/book.opf", f'<package xmlns="http://www.idpf.org/2007/opf" xmlns:opf="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>{title}</dc:title><dc:language>{language}</dc:language><dc:date>2010-01-01</dc:date><dc:publisher>Press</dc:publisher><dc:identifier opf:scheme="ISBN">9781234567897</dc:identifier>{creators}</metadata></package>')
    return file


@pytest.mark.parametrize("version", [2, 3])
def test_epub_roles(version, tmp_path):
    result = inspect_file(epub(tmp_path, version), {"title": "Being and Time", "author": "Heidegger", "mode": "exact", "translator": "Stambaugh", "editor": "Editor", "year": 2010, "language": "english"})
    assert result["status"] == "verified"
    assert result["checks"]["translator"] == "match"
    assert result["found"]["isbn"] == "9781234567897"
    assert {c["role"] for c in result["found"]["creators"]} == {"aut", "trl", "edt"}


def test_broken_epub_is_unverified(tmp_path):
    file = tmp_path / "broken.epub"
    file.write_bytes(b"PK\x03\x04junk")
    assert inspect_file(file)["reason"] == "unreadable"


def test_affirmative_conflict_and_absence(tmp_path):
    result = inspect_file(epub(tmp_path, language="de"), {"title": "Being and Time", "language": "english"})
    assert result["status"] == "mismatch"
    assert result["checks"]["language"] == "contradict"
    result = inspect_file(epub(tmp_path), {"title": "Being and Time", "mode": "exact", "volume": 2})
    assert result["status"] == "unverified"
    assert result["checks"]["volume"] == "absent"


def test_volume_conflict_keeps_affirmative_evidence(tmp_path):
    result = inspect_file(epub(tmp_path, title="Being and Time, Volume II"), {"title": "Being and Time", "volume": 1})
    assert result["status"] == "mismatch"
    assert result["checks"]["volume"] == "contradict"


def test_pdf_reader_optional(tmp_path, monkeypatch):
    file = tmp_path / "small.pdf"
    file.write_bytes(b"%PDF-1.4 synthetic")
    original = importlib.import_module
    def load(name):
        if name == "pypdf":
            raise ImportError("optional")
        return original(name)
    monkeypatch.setattr(importlib, "import_module", load)
    assert inspect_file(file)["reason"] == "no_pdf_reader"


def test_pdf_with_info_and_text_if_reader_installed(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Title": "Being and Time", "/Author": "Martin Heidegger"})
    file = tmp_path / "metadata.pdf"
    with file.open("wb") as stream:
        writer.write(stream)
    result = inspect_file(file, {"title": "Being and Time"})
    assert result["found"]["title"] == "Being and Time"
    assert result["status"] == "unverified"  # empty text is a scan


def test_other_format(tmp_path):
    assert inspect_file(tmp_path / "book.djvu")["reason"] == "format"
