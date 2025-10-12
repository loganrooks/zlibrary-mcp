# Project Plan: Z-Library MCP - Stabilization, Enhancement, and V1 Release

**Document Version:** 1.0
**Date:** 2025-05-06

## I. Introduction

The Z-Library MCP project has undergone initial development and end-to-end (E2E) testing. This process has identified several bugs, areas for codebase cleanup, and new feature requests. The primary goal of this project plan is to guide the development towards a stable V1 release, incorporating critical fixes and functionalities. Following V1, Phase 2 will focus on advanced search capabilities and further architectural enhancements.

This plan outlines a phased approach:
1.  **Phase 1:** Immediate cleanup, critical bug fixing (E2E failures), implementation of essential improvements like robust metadata scraping (`get_book_metadata`) and user-friendly filenames, and establishing solid version control. This phase culminates in V1 release readiness.
2.  **Phase 2:** Implementation of advanced search features (direct ISBN, DOI, etc., queries via `search_books`) and a holistic architectural review for future scalability.
3.  **Phase 3:** Ongoing iterative development and refinement.

## II. User Priorities Summary (as of 2025-05-06)

Based on recent user feedback and system analysis, the following priorities have been established:

*   **Codebase Cleanup:**
    *   `lib/python_bridge.py`: Refactor and remove deprecated logic.
    *   `zlibrary/src/zlibrary/libasync.py`: Address Pylance warnings and remove deprecated ID-based download logic.
*   **E2E Test Failures:**
    *   Resolve issues with `search_books` (language filter).
    *   Resolve issues with `full_text_search` (language, extension, no-result behavior, single-word phrase).
    *   Stabilize `download_book_to_file` (addressing `TypeError` and `FileExistsError`).
*   **New Features & Enhancements (V1 Critical):**
    *   **Implement `get_book_metadata` Tool:** This new tool is critical for V1. It must scrape all available metadata from a Z-Library book page URL, including but not limited to: Title, Author(s), Publisher, Publication Year, ISBN, DOI, Series, Language, Pages, Filesize, Description, Cover Image URL, Tags, "Most frequent terms" section, "Related booklists" URLs, and "You may be interested in" URLs.
    *   **Implement Enhanced Filename Convention:** Downloaded books should use the format: `LastnameFirstname_TitleOfTheBook_BookID.ext`.
*   **Process & Hygiene:**
    *   Address "git debt" by establishing and adhering to version control best practices (branching, commit messages).
    *   Deprecate and cleanly remove the `get_recent_books` tool.
*   **Deferred (Post-V1):**
    *   Direct implementation of advanced search fields (ISBN, DOI, Publisher, Author) into the `search_books` tool. Metadata for these fields will be gathered by `get_book_metadata` in V1.
*   **Overall Goal for V1:** A clean, organized, well-tested, and stable codebase with core functionalities and critical new tools implemented.

## III. Phase 1: Immediate Cleanup, Bug Fixing, and Foundational Improvements (Focus for V1 Release)

*   **Objective:** Stabilize the current codebase, address all critical E2E failures, implement essential low-level improvements (including robust metadata scraping via `get_book_metadata` and improved filenames), establish solid version control practices, and achieve V1 release readiness.

---

### Task 1: Resolve E2E Search Filter Failures

*   **Description:** Address failures identified by `qa-tester` ([2025-05-06 13:18:00] onwards) related to search filters in `search_books` (language filter) and `full_text_search` (language, extension, no-result behavior, single-word phrase issues).
*   **Dependencies:**
    *   **Technical Prerequisites:** Access to the Z-Library website for observing search behavior and HTML structure. Understanding of the existing search implementation in `zlibrary/src/zlibrary/libasync.py` and `zlibrary/src/zlibrary/abs.py`.
    *   **Sequential Prerequisites:** None for starting this task.
    *   **Subsequent Task Dependencies:** Full E2E Re-Testing (Phase 1, Task 7) depends on the resolution of these failures.
*   **Potential Challenges & Risks:**
    *   Z-Library website HTML structure changes impacting selectors.
    *   Complex interactions between different search parameters.
    *   Ambiguity in how Z-Library handles combined filters or specific edge cases (e.g., single-word phrase search without `words=True`).
    *   Rate limiting or IP blocking if testing involves frequent automated queries.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Optimal Architectural Layer:** Fixes will primarily reside within the `zlibrary` Python library (`libasync.py` for API calls, `abs.py` for parsing logic). The Python bridge (`lib/python_bridge.py`) and Node.js MCP server (`src/index.ts`, `src/lib/zlibrary-api.ts`) should require minimal changes unless parameter handling or schema definitions are affected.
    *   **Key Components/Modules:**
        *   `zlibrary/src/zlibrary/libasync.py`: Modify `AsyncZlib.search` and `AsyncZlib.full_text_search` to correctly construct search URLs and parameters.
        *   `zlibrary/src/zlibrary/abs.py`: Update `SearchPaginator.parse_page` if HTML structure related to filters or result presentation has changed.
    *   **Design Patterns/Principles:**
        *   Resilient parsing: Use robust selectors, handle missing elements gracefully.
        *   Clear error handling: Propagate meaningful errors if Z-Library returns unexpected results for filter combinations.
        *   Parameter validation: Ensure input parameters from MCP tools are correctly translated to Z-Library query parameters.
    *   **Data Flow:** MCP tool call (Node.js) -> Python Bridge -> `zlibrary` library -> Z-Library website -> `zlibrary` library (parse) -> Python Bridge -> Node.js -> MCP client. Input/output schemas for `search_books` and `full_text_search` tools in `src/index.ts` might need review if parameter interpretation changes.
*   **Mode Delegation Strategy:**
    *   `debug`: To investigate current live behavior of Z-Library search with problematic filters and analyze network requests/responses if necessary.
    *   `spec-pseudocode`: If filter logic is complex, to define the exact parameter mapping and conditional logic for URL construction.
    *   `code`: To implement the fixes in the Python library.
    *   `tdd`: To write unit tests for the Python library changes, focusing on filter parameter combinations and parsing of results.
*   **Verification & Testing Approach:**
    *   **Unit Tests:** (`tdd`) For `libasync.py` methods to ensure correct URL formation with various filter combinations. For `abs.py` parser to ensure correct data extraction with different filter-influenced results.
    *   **Integration Tests:** (`qa-tester`/`integration`) MCP tool-level tests (`search_books`, `full_text_search`) with specific filter inputs identified in `qa-tester` feedback.
    *   **Manual Verification:** (`qa-tester`/User) Re-run E2E test scenarios that previously failed.
*   **Impact Assessment:** Fixes will improve reliability of core search tools. May require updates to existing tests. No major impact on other system components expected, but `qa-tester` feedback logs will need to be updated.

---

### Task 2: Codebase Cleanup - Internal `zlibrary` library & `lib/python_bridge.py`

#### Task 2.1: `zlibrary/src/zlibrary/libasync.py` Cleanup

*   **Description:** Address Pylance warnings, remove all deprecated "get by id" logic, and ensure full alignment with ADR-002 download workflow (which relies on `bookDetails` from search, not direct ID lookups for downloads).
*   **Dependencies:**
    *   **Technical Prerequisites:** Understanding of ADR-002. Familiarity with Pylance diagnostics.
    *   **Sequential Prerequisites:** None.
    *   **Subsequent Task Dependencies:** Cleaner codebase benefits all subsequent development. `get_book_metadata` (Task 4) and Enhanced Filename (Task 3) will rely on a clean `bookDetails` structure.
*   **Potential Challenges & Risks:**
    *   Accidentally removing logic still in use if deprecation analysis is incomplete.
    *   Introducing regressions if refactoring is not carefully tested.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Optimal Architectural Layer:** Changes are confined to the `zlibrary` Python library (`libasync.py`).
    *   **Key Components/Modules:**
        *   `zlibrary/src/zlibrary/libasync.py`: Remove `get_by_id`-like methods or any internal functions solely supporting direct ID-based book fetching for download purposes. Refactor `download_book` to strictly use `bookDetails` as input. Address Pylance type hints, unused variables, etc.
    *   **Design Patterns/Principles:** DRY (Don't Repeat Yourself), Single Responsibility Principle (ensure `download_book` focuses on downloading given full details).
    *   **Data Flow:** Internal to `libasync.py`. The `download_book` function's input contract (expecting `bookDetails`) is reinforced.
*   **Mode Delegation Strategy:**
    *   `code`: To perform the refactoring and Pylance warning resolution.
    *   `tdd`: To ensure existing tests for `download_book` (and related functionalities) still pass after cleanup and to add tests if ADR-002 alignment reveals gaps.
*   **Verification & Testing Approach:**
    *   **Static Analysis:** (`code`) Pylance should report no relevant warnings after cleanup.
    *   **Unit Tests:** (`tdd`) Existing tests for `download_book` in `zlibrary/src/test.py` must pass. New tests might be needed to explicitly verify behavior with `bookDetails` as per ADR-002.
    *   **Integration Tests:** (`qa-tester`/`integration`) `download_book_to_file` tool should continue to function correctly.
*   **Impact Assessment:** Simplifies `libasync.py`, reduces dead code, and reinforces ADR-002. May require minor updates to Python unit tests if function signatures change.

#### Task 2.2: `lib/python_bridge.py` Cleanup

*   **Description:** Refactor/remove `_find_book_by_id_via_search` and any other functions reliant on direct ID lookups that are now deprecated by ADR-002. Ensure a clear interface and consistency with `libasync.py`.
*   **Dependencies:**
    *   **Technical Prerequisites:** Completion of Task 2.1 (or clear understanding of changes in `libasync.py`). Understanding of ADR-002.
    *   **Sequential Prerequisites:** Task 2.1.
    *   **Subsequent Task Dependencies:** Cleaner codebase benefits all subsequent development.
*   **Potential Challenges & Risks:**
    *   Ensuring all call sites of deprecated functions are updated or removed.
    *   Maintaining compatibility with Node.js layer if function signatures change.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Optimal Architectural Layer:** Changes are confined to the Python bridge (`lib/python_bridge.py`).
    *   **Key Components/Modules:**
        *   `lib/python_bridge.py`: Remove `_find_book_by_id_via_search`. Update `download_book` function to align with `libasync.py`'s `download_book` (expecting `bookDetails`). Remove any other helper functions that were solely for ID-based lookups for download.
    *   **Design Patterns/Principles:** Separation of Concerns (bridge focuses on interfacing, not complex lookup logic).
    *   **Data Flow:** The `download_book` function in the bridge will now expect `bookDetails` from the Node.js layer, aligning with ADR-002.
*   **Mode Delegation Strategy:**
    *   `code`: To perform the refactoring and removal of deprecated functions.
    *   `tdd`: To update Python bridge unit tests (`__tests__/python/test_python_bridge.py`) to reflect changes and ensure continued correct behavior of `download_book`.
*   **Verification & Testing Approach:**
    *   **Unit Tests:** (`tdd`) Existing tests for `download_book` in `test_python_bridge.py` must be updated and pass. Tests for removed functions should be deleted.
    *   **Integration Tests:** (`qa-tester`/`integration`) `download_book_to_file` MCP tool should continue to function correctly.
*   **Impact Assessment:** Simplifies `lib/python_bridge.py`. Reinforces ADR-002. Requires updates to Python bridge unit tests.

---

### Task 3: Implement Enhanced Filename Convention (`LastnameFirstname_TitleOfTheBook_BookID.ext`)

*   **Description:** Modify the book download process to save files using the specified user-readable format.
*   **Dependencies:**
    *   **Technical Prerequisites:** Access to `bookDetails` object (from search or `get_book_metadata`) which contains Author, Title, BookID, and original extension.
    *   **Sequential Prerequisites:** Task 2 (Codebase Cleanup) is beneficial for clarity on `bookDetails` sourcing. `get_book_metadata` (Task 4) could be an alternative source for metadata if search results are insufficient, but the primary source should be `bookDetails` passed to the download function.
    *   **Subsequent Task Dependencies:** Full E2E Re-Testing (Task 7).
*   **Potential Challenges & Risks:**
    *   Handling missing or malformed author/title data in `bookDetails`.
    *   Sanitizing strings to create valid filenames (removing special characters, handling long names).
    *   Ensuring consistency if author/title data can come from multiple sources (e.g., search vs. `get_book_metadata`).
*   **High-Level Technical Approach & Design Considerations:**
    *   **Optimal Architectural Layer:** The filename generation logic should reside in the Python bridge (`lib/python_bridge.py`) within the `download_book` function, as it's closest to the file saving operation and has access to `bookDetails`.
    *   **Key Components/Modules:**
        *   `lib/python_bridge.py`: Modify the `download_book` function (and potentially its counterpart in `libasync.py` if file naming is delegated there, though bridge is preferred).
        *   A new helper function for string sanitization and formatting (e.g., `_create_enhanced_filename(book_details)`) within `lib/python_bridge.py`.
    *   **Design Patterns/Principles:**
        *   Robust string sanitization: Use a whitelist of allowed characters or a comprehensive blacklist to prevent invalid filenames.
        *   Graceful degradation: Define fallback behavior if author or title is missing (e.g., `UnknownAuthor_Title_BookID.ext` or just `Title_BookID.ext`).
    *   **Data Flow:** The `bookDetails` object (containing author, title, bookID, extension) is passed to the `download_book` function. This function uses these details to construct the new filename before saving the downloaded content. The final `file_path` returned by the MCP tool will reflect this new convention.
*   **Mode Delegation Strategy:**
    *   `spec-pseudocode`: To define the precise rules for string sanitization, author name formatting (LastnameFirstname), and fallback mechanisms.
    *   `code`: To implement the filename generation and sanitization logic in `lib/python_bridge.py`.
    *   `tdd`: To write unit tests for the filename generation logic, covering various edge cases (special characters, missing data, long names).
*   **Verification & Testing Approach:**
    *   **Unit Tests:** (`tdd`) For the new filename generation/sanitization helper function in `lib/python_bridge.py`. Test cases should include:
        *   Standard author/title.
        *   Authors with multiple names.
        *   Titles with special characters, spaces, mixed case.
        *   Missing author/title.
        *   Different file extensions.
    *   **Integration Tests:** (`qa-tester`/`integration`) Call `download_book_to_file` MCP tool and verify the downloaded file has the correct name and extension.
*   **Impact Assessment:** Improves user experience by providing more informative filenames. Requires changes to file saving logic in the Python layer. Test assertions for downloaded file paths will need updates.

---

### Task 4: Implement `get_book_metadata` Tool (CRITICAL FOR V1)

*   **Description:** Create a new MCP tool that, given a Z-Library book page URL, scrapes and returns a comprehensive set of metadata. This includes: title, author(s), publisher, publication year, ISBN, DOI, series, language, pages, filesize, description, cover image URL, tags, "Most frequent terms" section, "Related booklists" URLs, and "You may be interested in" URLs.
*   **Dependencies:**
    *   **Technical Prerequisites:** Ability to make HTTP requests to Z-Library and parse HTML content.
    *   **Sequential Prerequisites:** None for starting design, but Python library cleanup (Task 2) is beneficial.
    *   **Subsequent Task Dependencies:** This tool is critical for V1 and will be used by other processes, potentially including future MCP-Vector-Database integration. Full E2E Re-Testing (Task 7).
*   **Potential Challenges & Risks:**
    *   **Z-Library HTML Structure Variability/Instability:** Selectors may break if the website changes. Different book pages might have slightly different layouts.
    *   **Missing Metadata Fields:** Not all books will have all metadata fields populated.
    *   **Complex Parsing Logic:** Extracting data from varied HTML structures can be complex (e.g., multiple authors, series information).
    *   **Rate Limiting/Anti-Scraping:** Frequent calls might be flagged.
    *   **Data Cleaning/Normalization:** Extracted data (e.g., author names, publisher) might need cleaning.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Optimal Architectural Layer:**
        *   **Scraping Logic:** Core scraping logic should reside in the `zlibrary` Python library (`libasync.py` or a new dedicated scraping module within it). This keeps Z-Library specific interactions encapsulated.
        *   **MCP Interaction:** Python bridge (`lib/python_bridge.py`) will expose this new library function. Node.js MCP server (`src/index.ts`, `src/lib/zlibrary-api.ts`) will define the tool schema and handler.
    *   **Key Components/Modules:**
        *   `zlibrary/src/zlibrary/libasync.py` (or new module): New async function `scrape_book_metadata(url: str) -> dict`. This function will use `httpx` to fetch the page and `BeautifulSoup4` to parse it.
        *   `lib/python_bridge.py`: New function `get_book_metadata(url: str)` that calls the library's scraping function.
        *   `src/lib/zlibrary-api.ts`: New function `getBookMetadata(url: string)` to call the Python bridge.
        *   `src/index.ts`: New MCP tool definition `get_book_metadata` with Zod input schema (`{ url: z.string().url() }`) and a comprehensive Zod output schema for the structured metadata.
    *   **Design Patterns/Principles:**
        *   **Resilient Scraping:** Use robust CSS selectors. Implement graceful error handling for each metadata field (e.g., return `null` or an empty list if a field is not found, rather than crashing).
        *   **Data Transformation Pipeline (Mini):** Raw scraped data -> Cleaning/Normalization -> Structured Output.
        *   **Separation of Concerns:** HTML fetching, parsing, and data structuring should be distinct logical steps.
        *   **Configuration (Optional):** Consider making selectors configurable if frequent changes are anticipated, though this adds complexity.
    *   **Data Flow:**
        1.  MCP Client calls `get_book_metadata` with a book page URL.
        2.  Node.js handler (`src/index.ts`) validates input.
        3.  `src/lib/zlibrary-api.ts` calls Python bridge.
        4.  `lib/python_bridge.py` calls `zlibrary/libasync.py::scrape_book_metadata(url)`.
        5.  `scrape_book_metadata` fetches HTML, parses it using BeautifulSoup, extracts all specified fields.
        6.  Extracted data (as a dictionary) is returned up the chain.
        7.  Node.js handler validates the output against its Zod schema and returns to client.
    *   **Output Schema (Zod in `src/index.ts`):**
        ```typescript
        // Example structure - to be refined
        const BookMetadataSchema = z.object({
          title: z.string().nullable(),
          authors: z.array(z.string()).nullable(), // Consider object for structured author if available
          publisher: z.string().nullable(),
          publicationYear: z.number().int().nullable(),
          isbn: z.string().nullable(), // Or array if multiple ISBNs (10, 13)
          doi: z.string().nullable(),
          series: z.string().nullable(), // Or object { name: string, numberInSeries: number }
          language: z.string().nullable(),
          pages: z.number().int().nullable(),
          filesize: z.string().nullable(), // e.g., "1.23 MB"
          description: z.string().nullable(),
          coverImageUrl: z.string().url().nullable(),
          tags: z.array(z.string()).nullable(),
          mostFrequentTerms: z.array(z.string()).nullable(),
          relatedBooklistUrls: z.array(z.string().url()).nullable(),
          youMayBeInterestedInUrls: z.array(z.string().url()).nullable(),
          sourceUrl: z.string().url() // The input URL, for reference
        });
        ```
*   **Mode Delegation Strategy:**
    *   `debug`/`architect`: To manually inspect several Z-Library book pages, identify robust CSS selectors for each metadata field, and understand HTML variations.
    *   `spec-pseudocode`: To define the detailed scraping logic for each field, error handling for missing fields, and the precise structure of the output metadata object (which will inform the Zod schema).
    *   `code`: To implement the scraping function in `libasync.py`, the bridge function, the Node.js API function, and the MCP tool definition with Zod schemas in `src/index.ts`.
    *   `tdd`: To write unit tests for:
        *   The Python scraping function (mocking HTTP responses with sample HTML, testing extraction of each field, handling missing fields).
        *   The Node.js Zod schemas (input and output validation).
*   **Verification & Testing Approach:**
    *   **Unit Tests:** (`tdd`)
        *   Python: Test `scrape_book_metadata` with various mocked HTML inputs (pages with all fields, some missing fields, different author/tag formats).
        *   Node.js: Test Zod schema validation for tool input and output.
    *   **Integration Tests:** (`qa-tester`/`integration`) Call the `get_book_metadata` MCP tool with a list of diverse live Z-Library book page URLs. Compare the output against manually verified metadata from those pages.
    *   **Manual Verification:** (`qa-tester`/User) Spot-check results for accuracy and completeness.
*   **Impact Assessment:** Introduces a critical new capability for metadata acquisition. This tool will be foundational for future features like advanced search indexing and rich book information display. Minimal impact on existing tools, but adds a new dependency on the stability of Z-Library's book page HTML structure.

---

### Task 5: Git Debt & Version Control Strategy

*   **Description:** Define and document a version control strategy (e.g., GitFlow, feature branches). Establish commit message conventions. Define how Memory Bank updates should be linked to or included in commits.
*   **Dependencies:**
    *   **Technical Prerequisites:** Understanding of Git.
    *   **Sequential Prerequisites:** None. This is a process task that can be defined early.
    *   **Subsequent Task Dependencies:** All subsequent development tasks will follow this strategy.
*   **Potential Challenges & Risks:**
    *   Ensuring team adherence to the chosen strategy.
    *   Overly complex strategy leading to developer friction.
    *   Poorly defined Memory Bank commit strategy leading to lost context or cluttered commit history.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Strategy Proposal:**
        *   **Branching Model:** Feature branches based off `main` (or a `develop` branch if preferred for V1 stabilization). `main` represents stable, releasable code.
            *   `feature/task-name` or `fix/issue-id`
            *   Pull Requests (PRs) to merge features into `main`/`develop`, requiring review (even if by the same developer initially, to establish the habit).
        *   **Commit Message Conventions:** Conventional Commits (e.g., `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`). Include a brief summary and optionally a more detailed body. Reference issue IDs if applicable.
        *   **Memory Bank & Commits:**
            *   Option A: Separate Commits: Code changes in one commit, related Memory Bank updates (e.g., new `activeContext.md` entries, `globalContext.md` decisions/patterns, mode-specific logs) in a subsequent commit with a message like `chore(memory): Update MB for feature X (commit Y)`. This keeps code commits clean.
            *   Option B: Part of Feature Commit: Include MB updates as part of the feature/fix commit, perhaps under a specific section in the commit message or as clearly named `.md` files in the commit. This keeps related changes together.
            *   **Recommendation:** Option A for clarity, but Option B might be simpler for a single developer. The key is consistency. SPARC rules already define when MB should be updated.
    *   **Documentation:** Create a `CONTRIBUTING.md` or a section in `README.md` detailing the strategy.
*   **Mode Delegation Strategy:**
    *   `devops`: To research standard branching models (GitFlow, GitHub Flow), propose a suitable strategy, define commit conventions, and document them. `devops` is also responsible for guiding the team on adherence.
    *   `architect`: To provide input on how the version control strategy supports the phased development plan and ensures architectural integrity through PR reviews (even if self-reviewed initially).
*   **Verification & Testing Approach:**
    *   **Process Verification:** (`devops`/User) Review commit history periodically to ensure adherence.
    *   **Documentation Review:** (`architect`/User) Ensure the documented strategy is clear and actionable.
*   **Impact Assessment:** Establishes a crucial process for collaborative and organized development. Improves traceability and code quality. Requires discipline from all modes/developers.

---

### Task 6: Deprecate and Remove `get_recent_books` Tool

*   **Description:** Cleanly remove the `get_recent_books` tool and its associated code from all layers of the application.
*   **Dependencies:**
    *   **Technical Prerequisites:** None.
    *   **Sequential Prerequisites:** None.
    *   **Subsequent Task Dependencies:** Full E2E Re-Testing (Task 7).
*   **Potential Challenges & Risks:**
    *   Missing a reference to the tool, leading to dead code or runtime errors if called.
    *   Incorrectly removing shared code used by other tools.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Removal Checklist:**
        1.  Node.js MCP Server (`src/index.ts`): Remove tool definition and Zod schemas.
        2.  Node.js API Layer (`src/lib/zlibrary-api.ts`): Remove `getRecentBooks` function.
        3.  Python Bridge (`lib/python_bridge.py`): Remove `get_recent_books` function.
        4.  `zlibrary` Python Library (`zlibrary/src/zlibrary/libasync.py`, `zlibrary/src/zlibrary/abs.py`): Remove `AsyncZlib.get_recent_books` method and any specific parsing logic in `abs.py` (e.g., within `SearchPaginator` if it had unique handling for recent books).
        5.  Tests: Remove associated tests in `__tests__/index.test.js`, `__tests__/zlibrary-api.test.js`, `__tests__/python/test_python_bridge.py`, and `zlibrary/src/test.py`.
        6.  Documentation: Remove any references from READMEs or other docs.
*   **Mode Delegation Strategy:**
    *   `code`: To perform the code removal across all layers and delete associated tests.
    *   `tdd`: To run all remaining test suites after removal to ensure no regressions were introduced and that shared code wasn't accidentally broken.
    *   `docs-writer`: To update documentation.
*   **Verification & Testing Approach:**
    *   **Static Analysis:** (`code`) Search codebase for "getRecentBooks" or "get_recent_books" to ensure all instances are removed.
    *   **Unit Tests:** (`tdd`) All existing test suites (`npm test`, `pytest`) must pass after removal.
    *   **Integration Tests:** (`qa-tester`/`integration`) Verify the tool is no longer listed or callable via MCP.
*   **Impact Assessment:** Reduces codebase size and complexity. Removes a potentially unmaintained feature. Test suites will shrink.

---

### Task 7: Full E2E Re-Testing (Post Phase 1 Changes)

*   **Description:** Conduct a comprehensive E2E test cycle to verify the stability of V1 after all Phase 1 changes are implemented.
*   **Dependencies:**
    *   **Technical Prerequisites:** All other Phase 1 tasks must be completed.
    *   **Sequential Prerequisites:** Tasks 1-6.
    *   **Subsequent Task Dependencies:** Successful completion is a gate for V1 release and commencement of Phase 2.
*   **Potential Challenges & Risks:**
    *   Discovery of new regressions introduced by Phase 1 changes.
    *   Time-consuming if many issues are found.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Scope:** Test all MCP tools, focusing on:
        *   Previously failed E2E scenarios (search filters, download stability).
        *   New functionalities (`get_book_metadata`, enhanced filenames).
        *   Core functionalities (`search_books`, `full_text_search`, `download_book_to_file` with and without RAG processing, `process_document_for_rag`).
        *   Error handling for invalid inputs or external API issues.
    *   **Success Criteria:** All defined E2E test scenarios pass. No critical or major bugs identified. System performs reliably under typical usage patterns.
*   **Mode Delegation Strategy:**
    *   `qa-tester`: To define the E2E test plan (reusing/updating existing plans), execute the tests manually or with any available test scripts, and document results.
    *   User: To participate in E2E testing, especially for workflows critical to their use case.
    *   `debug`: If new critical issues are found, `debug` will be engaged to diagnose.
*   **Verification & Testing Approach:**
    *   **E2E Test Execution:** (`qa-tester`/User) Follow the defined test plan.
    *   **Bug Reporting:** (`qa-tester`) Clearly document any failures with steps to reproduce, expected vs. actual results.
*   **Impact Assessment:** Provides confidence in V1 stability. May lead to further bug fixing tasks if issues are found.

## IV. Phase 2: Advanced Features & Future-Proofing (Post V1 Release)

*   **Objective:** Implement direct advanced search capabilities in `search_books` for robust MCP-Vector-Database integration, and further enhance the system architecture for future scalability and feature development.

---

### Task 1: Holistic Codebase Review & Architectural Design for Future Features (Post V1)

*   **Description:** After V1 is stable, conduct a comprehensive review of the entire codebase and system architecture. Identify areas for refactoring, and design for modularity and clear API contracts, especially to support direct advanced search (ISBN, DOI, etc.), further metadata extraction, and potential booklist interactions.
*   **Dependencies:**
    *   **Technical Prerequisites:** Stable V1 release.
    *   **Sequential Prerequisites:** Completion of Phase 1.
    *   **Subsequent Task Dependencies:** Designs from this task will guide Phase 2, Task 2 (Advanced Search Implementation) and other future developments.
*   **Potential Challenges & Risks:**
    *   Scope creep if too many refactoring areas are identified.
    *   Balancing ideal architectural changes with implementation effort.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Review Areas:**
        *   Python library (`zlibrary`): Modularity, clarity of `libasync.py` vs. `abs.py`, potential for dedicated modules (e.g., `scraping`, `search`).
        *   Python bridge (`lib/python_bridge.py`): Role and clarity of interface with Node.js.
        *   Node.js layer (`src/index.ts`, `src/lib/zlibrary-api.ts`): Tool handler complexity, schema management, error propagation.
        *   API contracts: Between Node.js and Python, and internal to Python library functions.
    *   **Design Goals for Advanced Search:**
        *   How will `search_books` handle field-specific queries (e.g., `isbn:`, `doi:`, `publisher:`)?
        *   How will these translate to Z-Library's underlying search syntax?
        *   Impact on `SearchBooksParamsSchema` in `src/index.ts`.
    *   **Architectural Principles:** Modularity, Separation of Concerns, Extensibility, Testability.
*   **Mode Delegation Strategy:**
    *   `architect`: To lead the review, identify refactoring candidates, and design architectural changes. To produce ADRs for significant changes.
    *   `holistic-reviewer`: To assist `architect` by performing a detailed scan of the codebase for anti-patterns, inconsistencies, or areas not adhering to established best practices.
    *   `spec-pseudocode`: To detail the API contracts and logic for new/modified components, especially for advanced search.
*   **Verification & Testing Approach:**
    *   **Design Review:** (`architect`/User) Review proposed architectural changes and ADRs.
    *   **Documentation:** (`architect`/`docs-writer`) Update architecture diagrams and documentation.
*   **Impact Assessment:** May lead to significant refactoring tasks. Will lay a stronger foundation for future features.

---

### Task 2: Implement Advanced Search Capabilities in `search_books`

*   **Description:** Enhance the `search_books` MCP tool to directly support field-specific queries for ISBN, DOI, Publisher, Author, etc. This involves translating these queries to Z-Library's search syntax and updating relevant schemas and code layers.
*   **Dependencies:**
    *   **Technical Prerequisites:** Design from Phase 2, Task 1. Understanding of Z-Library's advanced search syntax (if any, or how to emulate it).
    *   **Sequential Prerequisites:** Phase 2, Task 1.
    *   **Subsequent Task Dependencies:** Phase 2, Task 3 (Integration with MCP-Vector-Database).
*   **Potential Challenges & Risks:**
    *   Z-Library might not directly support all desired field-specific searches, requiring workarounds (e.g., combining general search with specific keywords).
    *   Complex parsing if Z-Library results for advanced queries differ significantly.
    *   Updating and testing all layers (Node.js schema, API, Python bridge, Python library).
*   **High-Level Technical Approach & Design Considerations:**
    *   **Optimal Architectural Layer:**
        *   **Search Syntax Translation & API Call:** `zlibrary/src/zlibrary/libasync.py` (within `AsyncZlib.search`).
        *   **Parameter Handling & Schema:** `src/index.ts` (update `SearchBooksParamsSchema`), `src/lib/zlibrary-api.ts`, `lib/python_bridge.py`.
    *   **Key Components/Modules:**
        *   `src/index.ts`: Update `SearchBooksParamsSchema` to include new optional fields (e.g., `isbn?: string`, `doi?: string`, `publisher?: string`, `author?: string`).
        *   `src/lib/zlibrary-api.ts`: Update `searchBooks` function to pass new parameters.
        *   `lib/python_bridge.py`: Update `search_books` function to accept and pass new parameters.
        *   `zlibrary/src/zlibrary/libasync.py`: Modify `AsyncZlib.search` to construct Z-Library search URLs based on the new fields. This is the core logic change.
    *   **Design Patterns/Principles:**
        *   Flexible query construction in `libasync.py`.
        *   Clear mapping from Zod schema fields to Z-Library query parameters.
    *   **Data Flow:** New optional parameters flow from MCP client -> Node.js -> Python Bridge -> `zlibrary` library, which constructs the specific Z-Library search query.
*   **Mode Delegation Strategy:**
    *   `spec-pseudocode`: To define the exact mapping of new input fields to Z-Library search query parameters and any conditional logic.
    *   `code`: To implement changes across all layers.
    *   `tdd`: To write unit tests for:
        *   Node.js Zod schema validation.
        *   Python library's `AsyncZlib.search` method with new field inputs.
        *   Python bridge parameter passing.
*   **Verification & Testing Approach:**
    *   **Unit Tests:** (`tdd`) As described above.
    *   **Integration Tests:** (`qa-tester`/`integration`) Call `search_books` MCP tool with various combinations of new advanced search fields. Verify results against manual Z-Library searches.
*   **Impact Assessment:** Significantly enhances search capabilities. Requires careful implementation and testing across multiple layers.

---

### Task 3: Integration with MCP-Vector-Database (Advanced Search)

*   **Description:** Define interaction patterns and data contracts for using the newly enhanced `search_books` tool (with direct advanced search fields) to query and potentially populate an MCP-Vector-Database. Plan testing for these direct advanced search queries in the context of vector DB integration.
*   **Dependencies:**
    *   **Technical Prerequisites:** Completion of Phase 2, Task 2. Access to and understanding of the MCP-Vector-Database's API/tools.
    *   **Sequential Prerequisites:** Phase 2, Task 2.
    *   **Subsequent Task Dependencies:** Future features relying on semantic search or vector-based recommendations.
*   **Potential Challenges & Risks:**
    *   Mismatch between Z-Library metadata structure and vector DB schema requirements.
    *   Performance of querying Z-Library and then vector DB in sequence.
    *   Complexity of data transformation if needed.
*   **High-Level Technical Approach & Design Considerations:**
    *   **Interaction Patterns:**
        *   **Query Augmentation:** User query -> `search_books` (with advanced fields if applicable) -> Z-Library results -> Extract key info/metadata -> Query MCP-Vector-Database with this info.
        *   **Direct Vector Search (if applicable):** User query -> Potentially transform query -> Directly query MCP-Vector-Database. (This task focuses on using `search_books` as a source).
    *   **Data Contracts:** Define how results from `search_books` (and `get_book_metadata`) are used to form queries for the vector DB. What fields are indexed in the vector DB?
    *   **Optimal Architectural Layer:** This is primarily an integration design task. The `architect` will define how the existing Z-Library MCP tools interact with another MCP (the vector DB). Actual calls to the vector DB would likely be orchestrated by an agent or a higher-level SPARC mode.
*   **Mode Delegation Strategy:**
    *   `architect`: To design the integration flow, define data contracts, and specify how `search_books` and `get_book_metadata` outputs are used with the vector DB.
    *   `spec-pseudocode`: To detail any data transformation logic required between Z-Library MCP output and vector DB input.
    *   `integration`/`qa-tester`: To plan and execute tests for workflows involving both Z-Library MCP and the vector DB.
*   **Verification & Testing Approach:**
    *   **Workflow Testing:** (`integration`/`qa-tester`) Define and test scenarios where `search_books` (using advanced fields) provides data that is then used to query the vector DB.
    *   **Data Consistency Checks:** Ensure metadata consistency between Z-Library results and vector DB entries if applicable.
*   **Impact Assessment:** Enables more powerful semantic search and recommendation capabilities by linking Z-Library data with a vector database. This is a significant architectural step.

## V. Phase 3: Ongoing Refinement & Future Releases

*   **Objective:** Standard SPARC cycle for iterative development of further features based on evolving user needs and system feedback.
*   **Tasks:**
    1.  **Iterative Feature Development:** Implement new features based on user requests and product roadmap (e.g., booklist interaction, deeper author/series analysis, user accounts/preferences if Z-Library API allows).
    2.  **Stabilization:** Ongoing bug fixing and performance optimization.
    3.  **Documentation:** Keep all documentation (user, developer, architecture) up-to-date.
    4.  **Deployment:** Manage releases and deployments as new stable versions are ready.
    *   *(Detailed architectural elaboration will be applied to each new feature in this phase as it's defined).*

## VI. General Procedures for All Phases

*   **Test-Driven Development (TDD) Workflow:**
    *   **Cycle:** For new features or significant bug fixes, the `tdd` mode will follow the Red-Green-Refactor cycle.
        *   **Red:** Write a failing test (or tests) that clearly defines the desired functionality or reproduces the bug. TDD anchors from `spec-pseudocode` will often inform this stage.
        *   **Green:** Write the minimal amount of code necessary to make the failing test(s) pass. `code` mode may assist if implementation details are complex and `tdd` mode struggles.
        *   **Refactor:** Clean up the code written in the Green phase, improve its structure, remove duplication, and ensure clarity, all while keeping the tests passing.
    *   **Scope:** TDD cycles should generally focus on one small, well-defined piece of functionality at a time to maintain a rapid feedback loop.
    *   **Mode Integration:**
        *   `spec-pseudocode` provides TDD anchors (test ideas/cases).
        *   `tdd` primarily executes the Red-Green-Refactor cycle.
        *   `code` can be delegated for the Green phase if `tdd` encounters significant implementation challenges beyond simple test-passing code.
        *   `devops` handles committing the work after each successful TDD cycle or at logical feature completion points.
*   **Version Control:**
    *   All development will follow the strategy defined in Phase 1, Task 5.
    *   Emphasis on feature branches (e.g., `feature/name` or `fix/name`) based off `main` (or `develop`).
    *   Pull Requests (PRs) for merging into `main`/`develop`, requiring review.
    *   **TDD Integration:**
        *   Commits can be made after each successful Red-Green-Refactor cycle for a small unit of work, or grouped logically for a completed feature/fix that involved multiple TDD cycles.
        *   Commit messages should clearly indicate the TDD cycle stage if committing mid-feature (e.g., `test(scope): Add failing test for X (Red)` , `feat(scope): Implement X to pass test (Green)` , `refactor(scope): Clean up X implementation (Refactor)`).
        *   Completed features/fixes developed via TDD should have a final commit message reflecting the overall change (e.g., `feat(search): Implement advanced ISBN search via TDD`).
    *   Commit messages will adhere to Conventional Commits.
    *   Memory Bank updates will be committed separately, referencing the related code commit.
*   **Verification and Regression Testing:**
    *   **Post-Task Verification:** After any task involving code changes (e.g., bug fix, feature implementation, refactoring), a full suite of relevant tests (unit, integration) must be run to verify the changes and check for regressions. This is typically the responsibility of the `tdd` mode or `qa-tester` for E2E.
    *   **Refactoring:** After any refactoring task (e.g., by `optimizer` or during a `tdd` Refactor phase), it is critical to run all affected unit and integration tests to ensure no behavior has inadvertently changed. The `tdd` mode is primarily responsible for this verification.
    *   **E2E Re-Testing:** Major milestones (like end of Phase 1) or significant feature integrations will trigger a full E2E re-testing cycle by `qa-tester` and the User.
*   **Memory Bank Usage:**
    *   Standard SPARC practice will be followed for comprehensive context logging, decision recording (ADRs, `globalContext.md`), pattern identification, and inter-mode communication.
    *   `activeContext.md` will be updated regularly.
    *   Mode-specific logs and feedback files will be maintained.
*   **User Involvement:**
    *   User review and approval will be sought for:
        *   This Project Plan document.
        *   Major feature specifications and architectural ADRs.
        *   Commit plans for significant refactors or removals.
    *   User participation will be crucial for E2E testing, especially for verifying V1 stability and new feature usability.
*   **Mode Delegation Strategy Overview:**
    *   SPARC modes will be orchestrated to leverage their specializations:
        *   **Specification & Design:** `architect` (high-level design, ADRs, system patterns), `spec-pseudocode` (detailed functional specs, algorithms, data transformations, TDD anchors).
        *   **Implementation:** `code` (for well-defined functions and components based on specs/passing TDD Green phase), `debug` (for intractable bugs or external API investigations).
        *   **Testing:** `tdd` (unit tests, full Red-Green-Refactor cycles for features/bugs, regression checks after refactoring), `qa-tester` (E2E testing, exploratory testing, test plan creation and execution), `integration` (verifying component interactions and end-to-end workflows).
        *   **Documentation:** `docs-writer` (user guides, technical documentation, API references, updating Memory Bank structure if needed).
        *   **Process & Infrastructure:** `devops` (version control management, CI/CD setup if applicable, deployment).
    *   Clear handovers between modes will be emphasized, with defined expected inputs and deliverables for each delegated task. Memory Bank will be the primary medium for context transfer.