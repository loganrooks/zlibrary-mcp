"""Run the live search assertions offline; never import their provider fixtures.

The subject is each live test body, not the search implementation. Payloads are
injected at its bridge/tool boundary so normalization cannot hide a bad oracle.
"""

import ast
import builtins
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest


LIVE_SOURCE = Path(__file__).parent / "integration" / "test_real_zlibrary.py"
SEARCH_CASES = [
    ("TestRealBasicSearch", "test_search_with_year_filter", "search"),
    ("TestRealBasicSearch", "test_search_with_language_filter", "search"),
    ("TestRealTermSearch", "test_term_search_with_filters", "search_by_term"),
    (
        "TestRealAuthorSearch",
        "test_search_author_with_comma_format",
        "search_by_author",
    ),
    ("TestRealAuthorSearch", "test_author_search_with_year_filter", "search_by_author"),
]
EMPTY_CASE = ("TestRealWorldEdgeCases", "test_empty_search_results", "search")


def extract_method(class_name, method_name, namespace):
    tree = ast.parse(LIVE_SOURCE.read_text(encoding="utf-8"))
    owner = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method = next(
        node
        for node in owner.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name
    )
    helpers = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_assert_")
    ]

    def forbid_import(*args, **kwargs):
        raise RuntimeError("Imports are forbidden inside the offline extracted body")

    namespace["__builtins__"] = {**vars(builtins), "__import__": forbid_import}
    exec(
        compile(
            ast.Module(body=[*helpers, method], type_ignores=[]),
            str(LIVE_SOURCE),
            "exec",
        ),
        namespace,
    )
    return namespace[method_name], {arg.arg for arg in method.args.args}


async def run_search_body(case, payload):
    class_name, method_name, endpoint = case

    async def respond(**kwargs):
        return deepcopy(payload)

    async def no_delay(seconds):
        return None

    namespace = {"asyncio": SimpleNamespace(sleep=no_delay)}
    if endpoint == "search":
        namespace["python_bridge"] = SimpleNamespace(search=respond)
    else:
        namespace[endpoint] = respond
    method, parameters = extract_method(class_name, method_name, namespace)
    fixtures = {"zlib_client": object()}
    if "credentials" in parameters:
        fixtures["credentials"] = {"email": "offline", "password": "offline"}
    await method(None, **fixtures)


def catalog_payload(case):
    method = case[1]
    return {
        "retrieved_from_url": "EAPI search: offline",
        "term": "philosophy",
        "author": "Hegel, Georg" if "comma" in method else "Hegel",
        "total_results": 1,
        "books": [
            {
                "id": "41",
                "title": "A catalog title",
                "year": 1820 if "author" in method else 2021,
                "language": "English",
            }
        ],
    }


@pytest.mark.parametrize("case", SEARCH_CASES, ids=lambda case: case[1])
@pytest.mark.parametrize("page_size", [1, 3])
async def test_positive_catalog_control(case, page_size):
    payload = catalog_payload(case)
    payload["books"] *= page_size
    payload["total_results"] = page_size
    await run_search_body(case, payload)


@pytest.mark.parametrize("case", SEARCH_CASES, ids=lambda case: case[1])
@pytest.mark.parametrize(
    "mutation",
    [
        "empty-catalog",
        "malformed-row",
        "missing-id",
        "blank-id",
        "missing-title",
        "blank-title",
        "placeholder-title",
        "second-row-malformed",
        "books-not-list",
        "missing-books",
        "empty-envelope",
    ],
)
async def test_catalog_mutants_are_rejected(case, mutation):
    payload = catalog_payload(case)
    if mutation == "empty-catalog":
        payload["books"] = []
        payload["total_results"] = 0
    elif mutation == "malformed-row":
        payload["books"] = [{}]
    elif mutation == "missing-id":
        del payload["books"][0]["id"]
    elif mutation == "blank-id":
        payload["books"][0]["id"] = " "
    elif mutation == "missing-title":
        del payload["books"][0]["title"]
    elif mutation == "blank-title":
        payload["books"][0]["title"] = " "
    elif mutation == "placeholder-title":
        payload["books"][0]["title"] = "N/A"
    elif mutation == "second-row-malformed":
        payload["books"].append({})
        payload["total_results"] = 2
    elif mutation == "books-not-list":
        payload["books"] = {}
    elif mutation == "missing-books":
        del payload["books"]
    else:
        payload = {}

    with pytest.raises(AssertionError):
        await run_search_body(case, payload)


@pytest.mark.parametrize(
    "case,field,value",
    [
        (SEARCH_CASES[0], "year", 2019),
        (SEARCH_CASES[0], "year", "unknown"),
        (SEARCH_CASES[1], "language", "French"),
        (SEARCH_CASES[1], "language", ""),
        (SEARCH_CASES[2], "year", 1999),
        (SEARCH_CASES[2], "language", "French"),
        (SEARCH_CASES[4], "year", 1851),
        (SEARCH_CASES[4], "year", ""),
    ],
    ids=[
        "basic-year-outside-range",
        "basic-year-unparseable",
        "basic-language-wrong",
        "basic-language-absent",
        "term-year-outside-range",
        "term-language-wrong",
        "author-year-outside-range",
        "author-year-absent",
    ],
)
async def test_filter_mutants_are_rejected(case, field, value):
    payload = catalog_payload(case)
    payload["books"][0][field] = value
    with pytest.raises(AssertionError):
        await run_search_body(case, payload)


@pytest.mark.parametrize("case", SEARCH_CASES[2:], ids=lambda case: case[1])
@pytest.mark.parametrize("total", [0, 2, "1", True])
async def test_returned_page_count_mutants_are_rejected(case, total):
    payload = catalog_payload(case)
    payload["total_results"] = total
    with pytest.raises(AssertionError):
        await run_search_body(case, payload)


async def test_empty_query_control_accepts_empty_list():
    await run_search_body(EMPTY_CASE, {"books": []})


@pytest.mark.parametrize(
    "payload",
    [{"books": [{}]}, {"books": {"id": "41"}}, {}],
    ids=["unexpected-row", "books-not-list", "empty-envelope"],
)
async def test_empty_query_mutants_are_rejected(payload):
    with pytest.raises(AssertionError):
        await run_search_body(EMPTY_CASE, payload)
