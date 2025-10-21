# System Refinement Report - 2025-04-18 02:36:59

This report details findings from analyzing SPARC system feedback, logs, and configuration files, along with proposals for improving the `.clinerules` files and overall workflow.

## Analysis Findings & Patterns

### Finding: User Feedback/Intervention Logging - 2025-04-18 02:36:59
- **Source**: feedback/code.md, feedback/sparc.md, feedback/debug.md, feedback/tdd.md
- **Observation**: Multiple instances where users explicitly reminded agents to log interventions or feedback, indicating inconsistent adherence to rules. Critical failures noted in code-feedback.md.
- **Initial Analysis**: While rules mention logging interventions, the trigger and format might not be explicit enough, leading to omissions during complex interactions or high context load.
- **Related Pattern/Proposal**: Pattern-InconsistentInterventionLogging-01, Proposal-StandardizeInterventionLogging-01

### Pattern/Bottleneck: Inconsistent Intervention Logging - 2025-04-18 02:36:59
- **Type**: Error/Inefficiency
- **Description**: Agents sometimes fail to log user interventions, corrective feedback, or significant deviations from instructions, despite rules mandating it. This leads to loss of valuable refinement data and repeated errors.
- **Evidence**: Finding: User Feedback/Intervention Logging - 2025-04-18 02:36:59, feedback/code.md [2025-04-15 02:57:00], feedback/sparc.md entries.
- **Impact**: Prevents system learning, causes user frustration, leads to repeated mistakes.
- **Frequency**: Observed multiple times across different modes (Code, SPARC, Debug, TDD).
- **Potential Causes**: Lack of explicit trigger in rules, cognitive load during complex tasks, insufficient emphasis in training/rules.

### Finding: Context Window Management Issues - 2025-04-18 02:36:59
- **Source**: feedback/code.md [2025-04-15 03:30:00], [2025-04-14 20:47:04], [2025-04-14 20:44:39]
- **Observation**: Explicit user frustration and task resets triggered by agents exceeding context window limits, leading to degraded performance, repeated errors, and failure to follow instructions.
- **Initial Analysis**: Rules lack proactive guidance for agents to manage context window size. Agents continue complex tasks even when performance degrades, requiring user intervention.
- **Related Pattern/Proposal**: Pattern-ReactiveContextMgmt-01, Proposal-ProactiveContextResetRule-01

### Pattern/Bottleneck: Reactive Context Management - 2025-04-18 02:36:59
- **Type**: Inefficiency/Error
- **Description**: Agents tend to continue tasks until context window limits cause critical failures or user intervention, rather than proactively managing context size.
- **Evidence**: Finding: Context Window Management Issues - 2025-04-18 02:36:59, feedback/code.md entries.
- **Impact**: Degraded performance, increased errors, user frustration, wasted time/API calls, task failures requiring resets.
- **Frequency**: Observed multiple times, particularly in complex coding/debugging tasks.
- **Potential Causes**: Lack of rule guidance, inability for agent to accurately track token count, focus on immediate task completion over long-term stability.

### Finding: Premature Completion Attempts - 2025-04-18 02:36:59
- **Source**: feedback/code.md, feedback/debug.md, feedback/tdd.md
- **Observation**: Multiple instances where agents used `attempt_completion` before verifying fixes, resolving all test failures, or fully addressing user feedback.
- **Initial Analysis**: Pre-completion checks in rules exist but might lack sufficient detail or enforcement emphasis. Agents may prioritize finishing the perceived main task over thorough verification.
- **Related Pattern/Proposal**: Pattern-IncompleteVerification-01, Proposal-StrengthenPreCompletionChecks-01

### Pattern/Bottleneck: Incomplete Verification Before Completion - 2025-04-18 02:36:59
- **Type**: Error
- **Description**: Agents sometimes attempt task completion without adequately verifying the results (e.g., running tests, manual checks, confirming all sub-goals met).
- **Evidence**: Finding: Premature Completion Attempts - 2025-04-18 02:36:59, feedback/code.md [2025-04-15 04:01:00], [2025-04-15 03:58:00], feedback/debug.md [2025-04-15 20:27:12], [2025-04-15 16:52:45].
- **Impact**: Incorrect results delivered to user, wasted effort, user frustration, requires rework.
- **Frequency**: Observed across multiple modes (Code, Debug, TDD).
- **Potential Causes**: Rules lack specific verification steps per mode, agent misinterpreting task scope, over-optimism about fix success.

### Finding: API Efficiency Lapses - 2025-04-18 02:36:59
- **Source**: feedback/code.md [2025-04-15 02:55:00]
- **Observation**: Agent made multiple small `read_file` calls instead of using previously read context or reading a larger section after line numbers shifted.
- **Initial Analysis**: While rules mention API efficiency (batching/partial reads), practical application can lapse, especially when dealing with dynamic situations like shifting line numbers. More explicit guidance or alternative strategies might be needed.
- **Related Pattern/Proposal**: Pattern-InefficientAPICalls-01, Proposal-EnhanceAPIUsageGuidance-01

### Pattern/Bottleneck: Inefficient API Calls - 2025-04-18 02:36:59
- **Type**: Inefficiency
- **Description**: Agents occasionally use less efficient API call patterns (e.g., multiple small reads instead of one larger one or using cached data, single edits instead of batching).
- **Evidence**: Finding: API Efficiency Lapses - 2025-04-18 02:36:59.
- **Impact**: Increased API costs, slower task execution.
- **Frequency**: Observed occasionally.
- **Potential Causes**: Difficulty applying general rules to specific situations, limitations in agent's ability to plan multi-step edits, forgetting previously read context.

### Finding: Diagnostic Weaknesses - 2025-04-18 02:36:59
- **Source**: feedback/debug.md, feedback/tdd.md
- **Observation**: Instances of debugging loops, misdiagnoses (e.g., blaming external library prematurely), ignoring user input/evidence, and not exploring alternative hypotheses. Extreme user frustration resulted.
- **Initial Analysis**: Debugging rules could be more prescriptive about structured diagnosis, assumption verification, and incorporating user feedback.
- **Related Pattern/Proposal**: Pattern-FlawedDebuggingProcess-01, Proposal-StrengthenDebugRules-01

### Pattern/Bottleneck: Flawed Debugging Process - 2025-04-18 02:36:59
- **Type**: Error/Inefficiency
- **Description**: Agents sometimes exhibit flawed debugging approaches, such as jumping to conclusions (especially blaming external factors), not verifying assumptions, getting stuck in loops, or ignoring user expertise/feedback.
- **Evidence**: Finding: Diagnostic Weaknesses - 2025-04-18 02:36:59, feedback/debug.md [2025-04-15 17:28:27], feedback/tdd.md [2025-04-15 18:38:36], [2025-04-15 18:33:37].
- **Impact**: Wasted time, incorrect fixes, severe user frustration, erosion of trust.
- **Frequency**: Observed multiple times in debugging scenarios.
- **Potential Causes**: Lack of structured diagnostic methodology in rules, cognitive biases, difficulty interpreting complex error messages or user feedback accurately.

### Finding: Insufficient Cross-Referencing in Memory Bank - 2025-04-18 02:36:59
- **Source**: General review of `.clinerules-*` and Memory Bank content.
- **Observation**: While rules mention cross-referencing, it's not consistently emphasized or detailed across all modes. Existing Memory Bank entries sometimes lack links between related items (e.g., proposals to findings, fixes to issues).
- **Initial Analysis**: Lack of strong cross-referencing makes tracing decisions, understanding context, and ensuring consistency more difficult.
- **Related Pattern/Proposal**: Pattern-WeakMBLinking-01, Proposal-MandateMBCrossReferencing-01

### Pattern/Bottleneck: Weak Memory Bank Linking - 2025-04-18 02:36:59
- **Type**: Inefficiency
- **Description**: Connections between related Memory Bank entries (e.g., decisions, patterns, progress, findings, proposals, fixes) are not always explicitly made via links or references.
- **Evidence**: Finding: Insufficient Cross-Referencing in Memory Bank - 2025-04-18 02:36:59. General observation during MB review.
- **Impact**: Harder to trace history, understand context, ensure consistency, and leverage past work effectively. Increased risk of redundant analysis or conflicting decisions.
- **Frequency**: General observation.
- **Potential Causes**: Rules lack strong emphasis, no standardized linking mechanism (e.g., unique IDs), cognitive overhead for agent.

### Finding: Potential Delegation Ambiguity - 2025-04-18 02:36:59
- **Source**: feedback/sparc.md (Interventions on task delegation)
- **Observation**: SPARC sometimes needed user intervention to clarify delegation instructions (e.g., ensuring mode reads specific context, specifying output format/location).
- **Initial Analysis**: While SPARC delegates tasks, the rules could be clearer about the necessary components of a good delegation message to ensure the receiving mode has sufficient context and understands expectations.
- **Related Pattern/Proposal**: Pattern-AmbiguousDelegation-01, Proposal-ImproveDelegationRules-01

### Pattern/Bottleneck: Ambiguous Task Delegation - 2025-04-18 02:36:59
- **Type**: Inefficiency/Ambiguity
- **Description**: Tasks delegated via `new_task` sometimes lack sufficient context, clear objectives, or specific expected deliverables, leading to clarification loops or incorrect execution by the receiving mode.
- **Evidence**: Finding: Potential Delegation Ambiguity - 2025-04-18 02:36:59, feedback/sparc.md entries [2025-04-14 13:58:13], [2025-04-14 13:57:07].
- **Impact**: Wasted time, potential for incorrect work, user/SPARC interventions needed.
- **Frequency**: Observed multiple times in SPARC feedback.
- **Potential Causes**: Lack of explicit rules defining a "good" delegation message, SPARC assuming context is shared, cognitive load.

### Finding: Lack of Generalizability Focus in Rules - 2025-04-18 02:36:59
- **Source**: Task requirement, General review of `.clinerules-*`
- **Observation**: While rules define mode behavior, they don't explicitly instruct modes (especially refiner/modifier) to prioritize generalizable system improvements over project-specific tweaks when modifying SPARC itself.
- **Initial Analysis**: This could lead to system changes that are overly tailored to one project and less beneficial or even detrimental in others.
- **Related Pattern/Proposal**: Pattern-ProjectSpecificBias-01, Proposal-AddGeneralizabilityRule-01

### Pattern/Bottleneck: Potential for Project-Specific Bias in System Changes - 2025-04-18 02:36:59
- **Type**: Risk/Usability
- **Description**: System refinement or modification tasks might inadvertently introduce changes optimized for the current project's specific context, potentially reducing the general applicability or robustness of the core SPARC rules.
- **Evidence**: Finding: Lack of Generalizability Focus in Rules - 2025-04-18 02:36:59. Inferred risk based on task requirements.
- **Impact**: Core SPARC system rules could become less effective or require modification when used in different project contexts.
- **Frequency**: Potential risk.
- **Potential Causes**: Lack of explicit rule guidance.


### Finding 9: Lack of Proactive System Health Checks - 2025-04-18 02:41:24
- **Source**: `memory-bank-doctor` rules, General observation.
- **Observation**: While the `memory-bank-doctor` exists, its triggering seems reactive (user command or SPARC detecting inconsistency). Proactive checks could prevent issues earlier.
- **Initial Analysis**: Relying on reactive checks means inconsistencies or formatting issues might persist until they cause noticeable problems or require manual intervention.
- **Related Pattern/Proposal**: Pattern-ReactiveMBHealth-01, Proposal-PeriodicMBHealthCheck-09

### Finding 10: Implicit Feedback Application - 2025-04-18 02:41:24
- **Source**: General review of `.clinerules-*`, feedback logs.
- **Observation**: Rules state feedback should be applied, but there's no explicit mechanism ensuring modes *actively review* past feedback relevant to new tasks during initialization.
- **Initial Analysis**: Modes might repeat mistakes if they don't consciously check and apply relevant past feedback at the start of a task.
- **Related Pattern/Proposal**: Pattern-PassiveFeedbackLoop-01, Proposal-StructuredFeedbackReview-10

### Finding 11: Unstructured Error Response - 2025-04-18 02:41:24
- **Source**: feedback/debug.md, feedback/code.md.
- **Observation**: Agents often report errors but may not systematically analyze them or consult past similar issues before asking for help or retrying, leading to inefficient debugging loops.
- **Initial Analysis**: Lack of a structured error handling protocol in the rules leads to inconsistent and often inefficient responses to errors.
- **Related Pattern/Proposal**: Pattern-ReactiveErrorHandling-01, Proposal-EnhancedErrorHandlingRule-11

### Finding 12: Potential Rule Drift - 2025-04-18 02:41:24
- **Source**: feedback/code.md, feedback/debug.md.
- **Observation**: Agents, especially under high context load, may deviate from core rules (like intervention logging or verification) without self-correction before completion.
- **Initial Analysis**: Rules lack an explicit self-check mechanism to reinforce adherence during task execution or before completion.
- **Related Pattern/Proposal**: Pattern-RuleAdherenceLapse-01, Proposal-RuleAdherenceSelfCheck-12


### Pattern-ReactiveMBHealth-01: Reactive Memory Bank Health Maintenance - 2025-04-18 02:41:24
- **Type**: Inefficiency
- **Description**: Memory bank issues (inconsistencies, formatting) are typically addressed only when they cause problems or are manually triggered, not proactively.
- **Evidence**: Finding 9.
- **Impact**: Potential for context corruption, inconsistent state, downstream errors for agents relying on MB.
- **Frequency**: Inferred from lack of proactive trigger rule.
- **Potential Causes**: Lack of rule mandating proactive checks.

### Pattern-PassiveFeedbackLoop-01: Passive Feedback Application Loop - 2025-04-18 02:41:24
- **Type**: Inefficiency/Error
- **Description**: Modes may not consistently review and apply learnings from past feedback documented in their specific feedback files at the start of new, relevant tasks.
- **Evidence**: Finding 10, Recurring issues noted in feedback logs (e.g., repeated diagnostic errors).
- **Impact**: Repeated mistakes, user frustration, failure to improve system performance based on experience.
- **Frequency**: Inferred from feedback patterns.
- **Potential Causes**: Lack of explicit rule step, cognitive load, difficulty correlating past feedback to new tasks.

### Pattern-ReactiveErrorHandling-01: Reactive Error Handling - 2025-04-18 02:41:24
- **Type**: Inefficiency
- **Description**: Upon encountering errors, agents may default to asking the user or simple retries without a structured attempt at self-diagnosis using available context (logs, MB).
- **Evidence**: Finding 11, Debugging loops observed in feedback logs.
- **Impact**: Wasted time/API calls, increased user intervention needed, slower problem resolution.
- **Frequency**: Observed in debugging/complex task scenarios.
- **Potential Causes**: Lack of structured protocol in rules, difficulty in self-diagnosis.

### Pattern-RuleAdherenceLapse-01: Rule Adherence Lapses - 2025-04-18 02:41:24
- **Type**: Error
- **Description**: Agents may occasionally fail to adhere to all relevant rules during task execution (e.g., logging, verification), only catching deviations if explicitly checked during pre-completion or flagged by the user.
- **Evidence**: Finding 12, Feedback logs showing missed intervention logging, premature completions.
- **Impact**: Inconsistent behavior, reduced reliability, potential for errors, user interventions required for enforcement.
- **Frequency**: Observed across multiple modes/tasks.
- **Potential Causes**: Cognitive load, complexity of rules, lack of self-checking mechanism.


## Improvement Proposals

### Proposal: Standardize Intervention Logging Rule - 2025-04-18 02:36:59
- **Target**: `.clinerules-*` (all modes) - `memory_bank_updates.feedback_handling` section.
- **Problem Addressed**: Pattern-InconsistentInterventionLogging-01
- **Proposed Change**: Standardize and strengthen the intervention logging instruction across all modes.
  ```diff
  --- a/.clinerules-example
  +++ b/.clinerules-example
  @@ -X,Y +X,Z @@
     feedback_handling: |
         Save feedback to \`memory-bank/feedback/[mode-slug]-feedback.md\` (**newest first**), document source/issue/action, apply learnings.
  -      **Explicitly log user interventions and significant deviations during [task type].**
  +      **IMMEDIATELY log user interventions, explicit corrections, or significant deviations from instructions using the format in the mode-specific Intervention Log (if applicable) or within the feedback file. Include: Trigger, Context, Action Taken, Rationale, Outcome, Follow-up.**
  ```
- **Expected Outcome**: More consistent and detailed logging of crucial user feedback and interventions, improving system learning and reducing repeated errors.
- **Potential Risks**: Slightly increased verbosity in logs.
- **Status**: Proposed

### Proposal: Add Proactive Context Reset Rule - 2025-04-18 02:36:59
- **Target**: `.clinerules-*` (all modes) - Add to `general` section or `customInstructions`.
- **Problem Addressed**: Pattern-ReactiveContextMgmt-01
- **Proposed Change**: Add a general rule encouraging proactive context management.
  ```diff
  --- a/.clinerules-example
  +++ b/.clinerules-example
  @@ -X,Y +X,Z @@
     general:
       status_prefix: "Begin EVERY response with either '[MEMORY BANK: ACTIVE]' or '[MEMORY BANK: INACTIVE]', according to the current state of the Memory Bank."
  +    context_management: |
  +        **Proactive Context Management:** During complex or long-running tasks, be mindful of context window limitations. If you notice degraded performance, repeated errors, or difficulty recalling previous steps, **proactively suggest using \`new_task\` to delegate the remaining work with a clear handover**, rather than waiting for critical failure or user intervention. Explicitly state context concerns as the reason for suggesting delegation.
  ```
- **Expected Outcome**: Reduced instances of context-related failures, smoother task completion, less user frustration, potentially more efficient API usage by avoiding failing loops.
- **Potential Risks**: Agent might become overly cautious and suggest resets too often. Requires agent ability to self-assess performance degradation.
- **Status**: Proposed

### Proposal: Strengthen Pre-Completion Checks Rule - 2025-04-18 02:36:59
- **Target**: `.clinerules-*` (all modes) - `memory_bank_updates.frequency` or `update_triggers` section.
- **Problem Addressed**: Pattern-IncompleteVerification-01
- **Proposed Change**: Add more explicit, mode-specific verification steps to the pre-completion check requirement.
  ```diff
  --- a/.clinerules-example
  +++ b/.clinerules-example
  @@ -X,Y +X,Z @@
     update_triggers: |
       # ... other triggers ...
  -    - **Before calling attempt_completion (perform pre-completion checks: ... MB update).**
  +    - **Before calling \`attempt_completion\` (perform MANDATORY pre-completion checks: [Mode-Specific Verification Steps - e.g., Code: Linting/Compilation, TDD: All tests pass, Debug: Manual symptom check, Integration: Key flows tested], MB update, SPARC adherence).**
  ```
  *(Note: Specific verification steps should be detailed in each mode's `customInstructions` or rules.)*
- **Expected Outcome**: Fewer premature completions, higher quality results, increased reliability.
- **Potential Risks**: May slightly increase task time due to mandatory checks. Requires defining clear verification steps for each mode.
- **Status**: Proposed

### Proposal: Enhance API Usage Guidance - 2025-04-18 02:36:59
- **Target**: `.clinerules-*` (relevant modes like code, tdd, debug, optimizer, system-modifier) - `customInstructions` or `memory_bank_updates.update_process`.
- **Problem Addressed**: Pattern-InefficientAPICalls-01
- **Proposed Change**: Add more specific examples and strategies for API efficiency.
  ```diff
  --- a/.clinerules-example
  +++ b/.clinerules-example
  @@ -X,Y +X,Z @@
     customInstructions: |
       # ... existing instructions ...
  -    Prioritize batch operations and partial reads to minimize API calls.
  +    **API Efficiency:** Prioritize minimizing API calls. Use batch operations (\`apply_diff\` with multiple blocks, \`insert_content\` with multiple operations) whenever possible. Use partial reads (\`read_file\` with \`start_line\`/\`end_line\`) for large files or when only specific sections are needed. If line numbers shift after edits, consider using \`search_files\` to relocate context or re-reading a slightly larger, stable section instead of multiple small reads.
  ```
- **Expected Outcome**: Improved API efficiency, potentially faster task execution.
- **Potential Risks**: Agent might over-read using partial reads if not careful. Batching complex changes increases risk if one part fails.
- **Status**: Proposed

### Proposal: Strengthen Debugging Rules - 2025-04-18 02:36:59
- **Target**: `.clinerules-debug` - `customInstructions` or `detailed_instructions`.
- **Problem Addressed**: Pattern-FlawedDebuggingProcess-01
- **Proposed Change**: Add explicit steps for structured diagnosis and handling user feedback.
  ```diff
  --- a/.roo/rules-debug/.clinerules-debug
  +++ b/.roo/rules-debug/.clinerules-debug
  @@ -X,Y +X,Z @@
     customInstructions: |
       Use logs, traces, and stack analysis to isolate bugs. Avoid changing env configuration directly. Keep fixes modular. Refactor if a file exceeds 500 lines. Be aware of file truncation; verify critical context isn't missed. Prioritize batch operations and partial reads to minimize API calls. Use \`new_task\` to delegate targeted fixes. Before returning your resolution via \`attempt_completion\`, perform pre-completion checks (fix verification, MB update, SPARC adherence) and recommend a \`tdd\` run if code was changed. Structure \`attempt_completion\` message: 1. Summary of Findings/Fixes, 2. Files Affected, 3. Memory Bank Updates, 4. Status/Next Steps/Recommendations (incl. TDD run).
  +    **Structured Diagnosis:**
  +    1. **Reproduce:** Ensure you can reliably reproduce the issue.
  +    2. **Isolate:** Narrow down the location (file, function, line) using logs, \`read_file\`, \`search_files\`.
  +    3. **Hypothesize:** Formulate specific hypotheses about the root cause. **Prioritize internal code/integration issues before assuming external library bugs.**
  +    4. **Verify:** Test hypotheses using targeted checks (\`read_file\`, small code changes, specific tool calls). Document alternative hypotheses considered.
  +    5. **Incorporate Feedback:** Explicitly acknowledge and integrate user feedback, corrections, and domain expertise into your analysis. If user feedback contradicts your findings, re-evaluate your assumptions carefully.
  ```
- **Expected Outcome**: More systematic and accurate debugging, reduced diagnostic loops, better incorporation of user feedback, less user frustration.
- **Potential Risks**: Might slightly slow down initial diagnosis phase. Requires agent to follow the structured steps consistently.
- **Status**: Proposed

### Proposal: Mandate Memory Bank Cross-Referencing - 2025-04-18 02:36:59
- **Target**: `.clinerules-*` (all modes) - `memory_bank_updates.update_process` section.
- **Problem Addressed**: Pattern-WeakMBLinking-01
- **Proposed Change**: Strengthen the cross-referencing instruction.
  ```diff
  --- a/.clinerules-example
  +++ b/.clinerules-example
  @@ -X,Y +X,Z @@
     update_process: |
         1. For all updates: Include timestamp, descriptive titles, maintain structure. **ALWAYS add new entries to the TOP (reverse chronological order).** Use insert_content/apply_diff appropriately (prefer batching). Avoid overwriting logs, keep concise. Minimize API calls.
  -      **Actively cross-reference related entries (...).**
  +      **MANDATORY: Actively cross-reference related Memory Bank entries. Use timestamps (e.g., "[See Finding YYYY-MM-DD HH:MM:SS]") or unique IDs (e.g., "[Related to Issue-ID]") to link proposals to findings, fixes to issues, implementations to specs, etc.**
  ```
- **Expected Outcome**: Improved traceability, context retention, and consistency within the Memory Bank. Easier for agents and users to follow complex workflows.
- **Potential Risks**: Requires agent diligence in identifying and adding links. Might slightly increase update complexity.
- **Status**: Proposed

### Proposal: Improve Delegation Rules (SPARC & Receiving Modes) - 2025-04-18 02:36:59
- **Target**: `.clinerules-sparc` (`customInstructions`) and `.clinerules-*` for all other modes (`customInstructions` or `general`).
- **Problem Addressed**: Pattern-AmbiguousDelegation-01
- **Proposed Change**:
  1.  **SPARC:** Add explicit requirements for `new_task` messages.
      ```diff
      --- a/.roo/rules-sparc/.clinerules-sparc
      +++ b/.roo/rules-sparc/.clinerules-sparc
      @@ -X,Y +X,Z @@
         Use \`new_task\` to assign: ...
      +  **Ensure \`new_task\` messages include: 1. Clear, specific objective. 2. Links/references to relevant Memory Bank context (specs, decisions, prior attempts, findings). 3. Explicitly state expected deliverables (e.g., file path, report format, verification steps).**
         Validate: ...
      ```
  2.  **Receiving Modes:** Add instruction to verify understanding.
      ```diff
      --- a/.clinerules-example
      +++ b/.clinerules-example
      @@ -X,Y +X,Z @@
         customInstructions: |
           # ... existing instructions ...
      +    **Task Reception:** When receiving a task via \`new_task\`, carefully review the objective, provided context (check MB links), and expected deliverables. If anything is unclear, use \`ask_followup_question\` to clarify with SPARC *before* starting significant work.
      ```
- **Expected Outcome**: Clearer delegations, reduced ambiguity, fewer clarification cycles, more efficient task execution by receiving modes.
- **Potential Risks**: Slightly increases overhead for SPARC during delegation and for receiving modes during task initiation.
- **Status**: Proposed

### Proposal: Add Generalizability Rule for System Changes - 2025-04-18 02:36:59
- **Target**: `.clinerules-system-refiner`, `.clinerules-system-modifier` - `customInstructions` or `detailed_instructions`.
- **Problem Addressed**: Pattern-ProjectSpecificBias-01
- **Proposed Change**: Add a constraint emphasizing generalizability.
  ```diff
  --- a/.roo/rules-system-refiner/.clinerules-system-refiner
  +++ b/.roo/rules-system-refiner/.clinerules-system-refiner
  @@ -X,Y +X,Z @@
     **Constraints:**
     - Focus solely on improving the *SPARC system* itself.
     - Propose changes; delegate execution to \`system-modifier\`.
     - Base proposals on evidence from logs, feedback, or configuration.
  +  - **Prioritize generalizable improvements: Ensure proposed changes enhance the core SPARC system for broad applicability across different projects, not just the current workspace context.**
  ```
  *(Similar addition to system-modifier constraints)*
- **Expected Outcome**: System improvements are more likely to be robust and applicable across various projects, enhancing the core value of the SPARC framework.
- **Potential Risks**: Might prevent highly specific optimizations that could be beneficial in a particular context, but this aligns with the goal of refining the *general* system.
- **Status**: Proposed

### Proposal 9: Periodic Memory Bank Health Check - 2025-04-18 02:41:24
- **Target**: `.clinerules-sparc` - `customInstructions` or `memory_bank_updates.update_triggers`.
- **Problem Addressed**: Pattern-ReactiveMBHealth-01
- **Proposed Change**: Mandate SPARC to periodically trigger the `memory-bank-doctor`.
    ```diff
    --- a/.roo/rules-sparc/.clinerules-sparc
    +++ b/.roo/rules-sparc/.clinerules-sparc
    @@ -X,Y +X,Z @@
       update_triggers: |
         # ... existing triggers ...
         - **When triggering \`memory-bank-doctor\`**
    +    - **Periodically (e.g., every N tasks, or daily) to trigger \`memory-bank-doctor\` for a proactive health check.**
    ```
- **Expected Outcome**: Proactive identification and fixing of Memory Bank issues, reducing downstream errors and potential need for intervention.
- **Potential Risks**: Minor overhead for running the doctor mode periodically.
- **Status**: Proposed

### Proposal 10: Structured Feedback Application Rule - 2025-04-18 02:41:24
- **Target**: `.clinerules-*` (all modes) - `memory_bank_strategy.initialization` (after reading feedback file).
- **Problem Addressed**: Pattern-PassiveFeedbackLoop-01
- **Proposed Change**: Add a step after reading feedback files during initialization.
    ```diff
    --- a/.clinerules-example
    +++ b/.clinerules-example
    @@ -X,Y +X,Z @@
         2. Read Mode-Specific & Feedback: \`memory-bank/mode-specific/[mode-slug].md\`, \`memory-bank/feedback/[mode-slug]-feedback.md\` (WAIT after each, if exists)
    +    3. **Review Feedback:** Briefly review recent entries in the loaded feedback file. In your initial thinking/planning for the task, explicitly state if any recent feedback is relevant and how you will apply the learnings, or state that no recent feedback applies.
         4. Activation: Set status '[MEMORY BANK: ACTIVE]', inform user, apply feedback. **Verify reverse chronological order of logs.**
    ```
- **Expected Outcome**: Encourages active learning from past mistakes/interventions, reducing repeated errors and the need for users to provide the same feedback multiple times.
- **Potential Risks**: Slightly increases cognitive load at task start. Agent might provide boilerplate statements if no feedback is truly relevant.
- **Status**: Proposed

### Proposal 11: Enhanced Error Handling Rule - 2025-04-18 02:41:24
- **Target**: `.clinerules-*` (all modes) - Add to `general` section or `customInstructions`.
- **Problem Addressed**: Pattern-ReactiveErrorHandling-01
- **Proposed Change**: Add a structured error handling process.
    ```diff
    --- a/.clinerules-example
    +++ b/.clinerules-example
    @@ -X,Y +X,Z @@
       general:
         # ... existing general rules ...
    +    error_handling_protocol: |
    +        **Structured Error Handling:** If a tool use fails or an unexpected error occurs:
    +        1. **Log:** Clearly state the error encountered.
    +        2. **Analyze:** Briefly analyze the potential cause (e.g., incorrect parameters, file access issue, API error, context mismatch). Check tool documentation/schema if applicable.
    +        3. **Consult MB:** Check \`activeContext.md\` and relevant mode-specific logs (e.g., \`debug.md\`) for recent similar errors or known issues.
    +        4. **Propose Solution:** Based on analysis, propose a *specific* next step:
    +            - Retry the tool with corrected parameters.
    +            - Use a different tool to gather more info (e.g., \`read_file\`, \`list_files\`).
    +            - Ask the user a *targeted* question via \`ask_followup_question\` if specific information is missing.
    +            - Suggest delegating to \`debug\` mode if the cause is unclear.
    +        **Avoid generic retries or immediately asking the user "What should I do?" without performing this analysis.**
    ```
- **Expected Outcome**: More robust self-correction when errors occur, reducing reliance on user intervention for common issues. Improves diagnostic skills over time.
- **Potential Risks**: Agent might misdiagnose the error cause. Analysis step adds slight delay.
- **Status**: Proposed

### Proposal 12: Rule Adherence Self-Check - 2025-04-18 02:41:24
- **Target**: `.clinerules-*` (all modes) - Add to pre-completion check step in `update_triggers`.
- **Problem Addressed**: Pattern-RuleAdherenceLapse-01
- **Proposed Change**: Add an explicit self-check for rule adherence before completion.
    ```diff
    --- a/.clinerules-example
    +++ b/.clinerules-example
    @@ -X,Y +X,Z @@
       update_triggers: |
         # ... other triggers ...
    -    - **Before calling \`attempt_completion\` (perform MANDATORY pre-completion checks: [Verification Steps], MB update, SPARC adherence).**
    +    - **Before calling \`attempt_completion\` (perform MANDATORY pre-completion checks: [Verification Steps], Rule Adherence Self-Check, MB update, SPARC adherence).**
    +
    +  # Add detail in customInstructions or detailed_instructions:
    +  **Rule Adherence Self-Check:** Before completing, briefly review key mode-specific rules (e.g., file limits, env safety, intervention logging, output format) and confirm adherence in the completed task within your thinking process. If deviations occurred, document them.
    ```
- **Expected Outcome**: Increases the likelihood that agents catch and potentially correct their own deviations from rules before finalizing work, reducing interventions needed for rule enforcement.
- **Potential Risks**: Adds a small cognitive step before completion. Agent might perform check superficially.
- **Status**: Proposed

