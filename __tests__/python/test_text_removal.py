"""Saved processing calls must not spend authentication or download resources."""

import json
import sys
from unittest.mock import AsyncMock

import pytest
import python_bridge


@pytest.mark.parametrize(
    "legacy",
    [
        {"process_for_rag": True},
        {"process_for_rag": "false"},
        {"process_for_rag": None},
        {"processed_output_format": "txt"},
        {"processed_output_format": None},
    ],
)
async def test_removed_options_refused_before_provider_contact(
    legacy, monkeypatch, capsys
):
    login = AsyncMock()
    download = AsyncMock()
    monkeypatch.setattr(python_bridge, "initialize_eapi_client", login)
    monkeypatch.setattr(python_bridge, "get_eapi_client", download)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "python_bridge.py",
            "download_book",
            json.dumps(
                {
                    "book_details": {"id": "1", "hash": "test"},
                    "output_dir": "/unused",
                    **legacy,
                }
            ),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        await python_bridge.main()
    assert exc.value.code == 1
    assert "Text processing was removed in 2.0" in capsys.readouterr().err
    login.assert_not_awaited()
    download.assert_not_awaited()


async def test_direct_python_call_refuses_processing_before_provider(monkeypatch):
    provider = AsyncMock()
    monkeypatch.setattr(python_bridge, "get_eapi_client", provider)
    with pytest.raises(ValueError, match="Text processing was removed in 2.0"):
        await python_bridge.download_book({"id": "1"}, "/unused", process_for_rag=True)
    provider.assert_not_awaited()
