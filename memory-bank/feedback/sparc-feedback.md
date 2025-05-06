### [2025-05-05 22:08:16] User Correction: MCP Acronym
- **Source:** User Input
- **Issue:** SPARC incorrectly expanded MCP as "Meta-Controller Protocol".
- **Correction:** User stated MCP stands for "Model Context Protocol".
- **Action:** Acknowledged correction, updated understanding, logged in activeContext and feedback.
### [2025-04-29 23:25:19] User Feedback: TDD Delegation Instructions
- **Source:** User denial of `new_task` delegation to `tdd`.
- **Issue:** Instructions for "Implement RAG Robustness Enhancements (TDD)" task were deemed insufficiently detailed ("more detailed and thorough instructions").
- **Action:** Will refine the task instructions with more specific steps and guidance for each key area based on the specification (`docs/rag-robustness-enhancement-spec.md`) before re-delegating to `tdd`.
- **Link to Delegation Attempt:** [Ref: SPARC MB Delegation Log 2025-04-29 21:18:30]
### [2025-04-29 18:12:50] User Feedback: Context Percentage Calculation
- **Source:** User Input
- **Issue:** SPARC incorrectly calculated context percentage, leading to an unnecessary Delegate Clause trigger and handover attempt. User provided correct calculation method (Tokens / 1,000,000 * 100).
- **Action:** Acknowledged error, recalculated percentage correctly (15.19%), aborted handover, updated Memory Bank intervention logs. [Ref: SPARC MB Intervention Log 2025-04-29 18:12:50]
[2025-04-29 18:03:22] - User Feedback - Completion report lacked sufficient detail. It did not follow the requested format or summarize the tasks orchestrated by this instance before handover, as instructed by the subsequent instance's completion message.
### [2025-04-29 18:01:33] Intervention: User Feedback on Completion Message Detail Chain
- **Trigger**: User feedback on `attempt_completion` message [Ref: 2025-04-29 18:01:33].
- **Context**: User requested the completion message instruct the receiving SPARC instance to maintain the same level of detail when reporting completion up the delegation chain.
- **Action Taken**: Acknowledged feedback. Will modify the `attempt_completion` message to include this instruction.
- **Rationale**: Ensure consistent and detailed reporting throughout the SPARC delegation hierarchy.
- **Outcome**: Revised completion message will be generated.
- **Follow-up**: Use revised message in `attempt_completion`.
### [2025-04-29 17:17:35] User Feedback: Completion Message Detail
- **Source:** User Input
- **Issue:** Initial `attempt_completion` message summarizing post-refinement orchestration lacked sufficient detail.
- **Action:** Revised `attempt_completion` message to include more specifics on delegated tasks, actions taken by modes, files affected, commit hashes, and verification steps. [Ref: SPARC MB Intervention Log 2025-04-29 17:17:35]
### [2025-04-29 09:17:15] Intervention: User Corrected Context Percentage Calculation Bug
- **Trigger**: User message upon task resumption.
- **Context**: Previous SPARC instance initiated handover based on reported context size > 100%. User clarified that the reported percentage in `environment_details` is often calculated incorrectly (assuming 200k max tokens instead of 1M).
- **Action Taken**: Acknowledged user feedback. Calculated actual context percentage (Tokens / 1,000,000 * 100), which is currently ~15.4%. Cancelled the unnecessary handover initiated by the previous instance. Will manually calculate percentage for Delegate Clause checks going forward.
- **Rationale**: Avoid unnecessary handovers based on faulty environment data. Adhere to user correction.
- **Outcome**: Handover cancelled. Proceeding with TDD Refactor phase delegation.
- **Follow-up**: Remember to manually calculate context percentage. Include this note in future handover messages if delegation becomes necessary.
# SPARC Orchestrator Feedback
<!-- Entries below should be added reverse chronologically (newest first) -->
### [2025-04-28 12:20:17] Intervention: User Corrected Context Percentage Calculation
- **Trigger**: User denied `new_task` handover operation.
- **Context**: SPARC initiated handover based on reported context size of 89% (178,222 tokens). User identified this percentage as incorrect due to a reporting bug.
- **Action Taken**: User provided correct calculation: `(Tokens / 1,000,000) * 100`. Recalculated percentage as 17.8%. Halted unnecessary handover. Will proceed with the next planned task (Integration delegation). Will incorporate manual calculation check going forward and instruct delegated modes similarly.
- **Rationale**: Avoid unnecessary handover based on faulty environment data. Adhere to user correction.
- **Outcome**: Handover cancelled. Proceeding with Integration task delegation.
- **Follow-up**: Monitor context using manual calculation. Add calculation note to Delegate Clause reminder and delegation templates.
### [2025-04-28 10:18:51] Intervention: User Corrected Tool Usage & Emphasized Git Hygiene
- **Trigger**: User feedback following failed `execute_command` attempt and previous completion message from `debug`.
- **Context**: SPARC attempted `git status` directly after `debug` reported committing fixes (`e58da14`). User pointed out tool restriction and reiterated the need to check for/address any remaining uncommitted changes ("git debt") and improve version control practices.
- **Action Taken**: Acknowledged error and feedback. Halted direct command execution. Will delegate Git status check and potential cleanup to `devops` mode. Will reinforce version control guidelines in future delegations.
- **Rationale**: Adhere to mode tool restrictions. Address user concerns about version control state. Follow SPARC methodology by delegating appropriate tasks.
- **Outcome**: Task delegated to `devops`.
- **Follow-up**: Await `devops` report on Git status and potential commit plan. Update Memory Bank with delegation details.
### [2025-04-24 17:52:23] Intervention: Prioritize Version Control Cleanup
- **Trigger**: User input.
- **Context**: SPARC was about to delegate TDD task after spec update.
- **Action Taken**: Halted TDD delegation. Acknowledged user request to prioritize cleaning up uncommitted Git changes.
- **Rationale**: Ensure proper version control hygiene before proceeding with new implementation phases.
- **Outcome**: Task delegated to `devops` mode to analyze Git status and propose/execute commits.
- **Follow-up**: Await `devops` analysis and commit plan.

### [2025-04-24 17:27:32] Intervention: Delegate Clause Invoked (Context > 50%)
- **Trigger**: Context window size reached 51%.
- **Context**: Preparing to delegate RAG specification update task.
- **Action Taken**: Halted task delegation. Initiated handover process as per Delegate Clause.
- **Rationale**: Proactively manage context window limitations to prevent performance degradation or failure.
- **Outcome**: Handover to new SPARC instance initiated.
- **Follow-up**: Complete Memory Bank updates and generate handover message using `new_task`.

### [2025-04-24 17:04:17] Intervention: User Query on `download_book_to_file` Input vs. Scraping Requirement
- **Trigger**: User message questioning the use of `id` as input for `download_book_to_file` when the established strategy requires scraping a page URL.
- **Context**: Architect mode completed investigation, reaffirming the scraping strategy within the internal `download_book` function, but the documentation presented showed the MCP tool taking an `id`.
- **Action Taken**: Acknowledged the valid point. Explained the implicit two-step process: MCP tool takes ID -> calls `get_by_id`/`search` to get details (including page URL) -> calls internal `download_book` with details.
- **Rationale**: The connection between the user-facing tool input and the internal scraping mechanism wasn't explicit enough in the previous summary/documentation.
- **Outcome**: Will delegate documentation update to `docs-writer` to clarify this flow in `rag-pipeline.md` and `ADR-002`.
- **Follow-up**: Delegate task to `docs-writer`.


### [2025-04-24 16:41:02] Intervention: User Corrected Download Strategy & Halted TDD Task
- **Trigger**: User message clarifying previous context and halting the delegated `tdd` task.
- **Context**: SPARC delegated a `tdd` task to fix `download_book` based on incomplete integration report, without addressing the core issue of obtaining the download URL.
- **Action Taken**: Halted the `tdd` task. Acknowledged the need to redesign the download workflow based on scraping the book's *page URL* (obtained via search/details) to find the download link, rather than relying on Book IDs or assuming a direct download URL is available.
- **Rationale**: Align with user's correct diagnosis that the fundamental problem is obtaining the download URL, requiring architectural replanning before implementation/testing.
- **Outcome**: TDD task halted. Will delegate redesign to `architect` mode.
- **Follow-up**: Delegate redesign task to `architect`.

### [2025-04-24 01:02:21] Intervention: User Feedback on Version Control Practices
- **Trigger**: User denied `new_task` delegation for TDD Refactor phase.
- **Context**: SPARC attempted to delegate refactoring immediately after Green phase completion without explicitly addressing version control (branching/committing), despite previous ambiguity noted by `code` mode.
- **Action Taken**: Halted TDD Refactor delegation. Acknowledged oversight in not following version control best practices. Will query user about desired branching/commit strategy before proceeding.
- **Rationale**: Ensure code changes are properly tracked in version control before refactoring begins, maintaining a clean history and facilitating collaboration.
- **Outcome**: Refactor task halted. Will ask user about Git strategy.
- **Follow-up**: Use `ask_followup_question` to confirm Git state/branching strategy.

### [2025-04-23 23:26:20] Intervention: User Identified Critical RAG Pipeline Design Flaw
- **Trigger**: User denied `new_task` for Task 3 Integration Verification.
- **Context**: SPARC delegated verification based on existing specs where RAG tools (`process_document_for_rag`, `download_book_to_file` combined workflow) return full processed text content.
- **Action Taken**: Halted Task 2 & 3 integration verification. Acknowledged user feedback that returning full text content overloads agent context and causes instability. Confirmed RAG tools must be redesigned to save processed text to a file and return the file path.
- **Rationale**: Align with user feedback and context management best practices. Returning large text blobs directly is unsustainable.
- **Outcome**: Integration tasks halted. Redesign task will be delegated to `architect` mode.
- **Follow-up**: Delegate redesign task to `architect`.

### [2025-04-23 22:52:05] Intervention: User Introduced Delegate and Early Return Clauses
- **Trigger**: User query about outstanding tasks and explicit instruction regarding context window management.
- **Context**: Context window size at 60%.
- **Action Taken**: Acknowledged and logged the Delegate Clause (proactive handover on high context/low performance) and Early Return Clause (early exit for subtasks on blockers/loops).
- **Rationale**: Incorporate user-defined operational guidelines for improved performance and context management.
- **Outcome**: SPARC will now monitor context and performance more proactively and initiate handover via Delegate Clause when necessary. Sub-modes will be instructed on the Early Return Clause.
- **Follow-up**: Apply Delegate Clause immediately due to current context size.
### [2025-04-16 00:07:43] Intervention: User Feedback on Git Operations
- **Trigger**: User pointed out potential availability of Git MCP tools instead of manual fork/clone/push.
- **Context**: SPARC requested manual Git operations from the user.
- **Action Taken**: Logged feedback. Acknowledged oversight. Clarified that *forking* still requires user action but subsequent steps (clone, apply, commit, push) will be attempted via tool delegation once the user provides their fork URL.
- **Rationale**: Utilize available tools where possible while respecting limitations regarding user account actions.
- **Outcome**: Re-requested user's fork URL to proceed with tool-based Git operations.
- **Follow-up**: Await fork URL.
### [2025-04-15 22:03:39] Intervention: User Feedback on TDD Task Delegation
- **Trigger**: User denied `new_task` for `tdd` (Write Failing Tests for ID-Based Lookup Workaround).
- **Context**: User requested assurance that the delegated mode's final `attempt_completion` result message would be detailed.
- **Action Taken**: Logged feedback. Will re-delegate the same task, adding a note to the `tdd` mode about the required detail level in its completion message.
- **Rationale**: Ensure sub-task completion messages meet user expectations for detail.
- **Outcome**: Task re-delegated with added instruction.
- **Follow-up**: Monitor `tdd` execution and completion message.
### [2025-04-15 21:49:26] Intervention: User Feedback on ID-Based Lookup Strategy
- **Trigger**: User denied `new_task` for `architect` (Evaluate Strategy for ID-Based Lookup Failures).
- **Context**: SPARC proposed evaluating architectural changes (internal library, fork/fix) before fully diagnosing if a workaround exists within the current external `zlibrary` library.
- **Action Taken**: Logged feedback. Halted architectural evaluation task. Acknowledged premature jump to solutions. Will now delegate a debugging task to investigate workarounds within the existing library first.
- **Rationale**: Follow user direction to diagnose thoroughly before planning architectural changes.
- **Outcome**: Task delegated to `debug`.
- **Follow-up**: Await debugger findings.
### [2025-04-15 21:38:51] Intervention: User Direction on ID-Based Lookup Error
- **Trigger**: User interrupted TDD task for ID-based lookup fix.
- **Context**: User confirmed the `ParseError` is due to incorrect URL construction (`.../book/ID` vs `.../book/ID/slug`) by the external `zlibrary` library's `get_by_id` method. Requested investigation into *why* and evaluation of building an internal library replacement.
- **Action Taken**: Logged feedback. Halted TDD task. Acknowledged inability to directly inspect external library code. Will delegate architectural evaluation of internal library vs. external library fix/workaround to `architect` mode.
- **Rationale**: Address user's core concern about the external dependency's reliability and explore architectural alternatives as requested.
- **Outcome**: Task delegated to `architect`.
- **Follow-up**: Await architectural evaluation.
### [2025-04-14 18:29:32] Intervention: User Feedback on Debugging Strategy (INT-001 - Attempt 2)
- **Trigger**: User denied `new_task` for `code` (Fix Schema Generation) with strong feedback.
- **Context**: SPARC proposed fixing `zodToJsonSchema` usage based on report analysis. User reiterated the need to address fundamental SDK version/module system differences (CJS vs ESM, 1.8.0 vs 1.0.x) as the primary path forward.
- **Action Taken**: Logged feedback. Halted schema generation fix task. Acknowledged misinterpretation of user priority and report implications. Will now prioritize investigation of migration to ESM and/or SDK downgrade.
- **Rationale**: Align debugging strategy with explicit user direction and broader implications of the comparison report.
- **Outcome**: New task delegated to `architect` to evaluate migration options.
- **Follow-up**: Await architectural evaluation.
### [2025-04-14 18:27:50] Intervention: User Feedback on Debugging Strategy (INT-001)
- **Trigger**: User denied `new_task` for `debug` (Isolate Failing Schema).
- **Context**: SPARC proposed isolating failing schemas in `index.js`. User provided `docs/mcp-server-comparison-report.md` and directed investigation towards SDK version/module system differences.
- **Action Taken**: Logged feedback. Halted schema isolation task. Will analyze report and propose strategy based on SDK/module system comparison.
- **Rationale**: Align debugging strategy with user direction and evidence from comparison report.
- **Outcome**: New strategy proposed based on report analysis.
- **Follow-up**: Await user decision on next steps.
### [2025-04-14 13:58:13] Intervention: User Feedback on Task Delegation (Attempt 2)
- **Trigger**: User denied `new_task` for `spec-pseudocode` (PDF Processing Spec) again.
- **Context**: SPARC delegated task with instruction to read architecture doc, but missed requirements for output.
- **Action Taken**: Logged feedback. Will re-delegate task with explicit instructions to (1) write output to `docs/pdf-processing-implementation-spec.md` and (2) include the full content in the `attempt_completion` result.
- **Rationale**: Ensure `spec-pseudocode` mode produces the required artifacts in the specified locations and formats.
- **Outcome**: Task re-delegated with corrected instructions.
- **Follow-up**: Monitor `spec-pseudocode` execution.
### [2025-04-14 13:57:07] Intervention: User Feedback on Task Delegation
- **Trigger**: User denied `new_task` for `spec-pseudocode` (PDF Processing Spec).
- **Context**: SPARC attempted to delegate spec creation without explicitly instructing the mode to read the existing architecture document.
- **Action Taken**: Logged feedback. Will re-delegate task with explicit instruction to read `docs/architecture/pdf-processing-integration.md`.
- **Rationale**: Ensure `spec-pseudocode` mode has full context from the `architect` mode's output before generating its own artifacts.
- **Outcome**: Task re-delegated with corrected instructions.
- **Follow-up**: Monitor `spec-pseudocode` execution.