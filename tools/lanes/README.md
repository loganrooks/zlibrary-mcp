# Optional Codex development lane

Status: **preliminary v0-trial**. The [manifest](manifests/codex-development.json)
is an optional offline development template, not a shipped launcher, permanent
profile policy or authorization to work. Manual Codex launch under the same
owning brief and [repository contract](../../AGENTS.md) remains an alternative.

## Supply authority and preview

1. Supply an explicitly chosen external preliminary `launch_lane.py` compatible
   with `preliminary v0-trial`. Read its accompanying `FORMAT.md` and `README.md`.
   No launcher is bundled here; do not install one or change global settings.
2. Supply a current `BRIEF.md` in the owned lane. It must identify the source of
   authority (path and line), standing sequence/holds, checkout and owned files,
   side-effect limits, required sources, deterministic checks and return files.
   A profile name or a project mention is not authorization. Resolve holds first.
3. Copy the template to an owned review location. Set a unique lane name,
   decision/provenance, current `sequencing.source` and `standing`, and task for
   that BRIEF. Keep agent proposals distinct from operator decisions. Do not
   put secrets, private paths, transcripts or account settings in the manifest.
4. From the repository root, preview using supplied absolute paths:

   ```sh
   LANE_LAUNCHER='/absolute/path/to/supplied/launch_lane.py'
   LANE_MANIFEST='/absolute/path/to/reviewed/codex-development.json'
   LANE_DIR='/absolute/path/to/owned-lane-with-BRIEF'
   python3 -I -B "$LANE_LAUNCHER" "$LANE_MANIFEST" \
     --lane-dir "$LANE_DIR" --dry-run
   ```

   Python 3.11+ is required by the external launcher's stdlib `tomllib` import;
   the selected Codex executable must already exist. Dry-run previews argv; it
   does not create a workspace, start Codex or authorize a real launch. This
   launcher's CLI inventories user/ancestor configuration for MCP identifiers.
   If configuration reads are outside the BRIEF, **do not run that CLI**: have
   the owner perform the preview, or import the supplied launcher with bytecode
   writes disabled and call `validate` / `compile_manifest` with synthetic MCP
   identifiers for an offline contract check. Synthetic identifiers do not
   establish the actual configured inventory.

## Scope and checks

The requested configuration is GPT-6.1 Sol, high effort, shell,
`workspace-write` / `on-request`, network and web search disabled, no enabled
MCP (explicitly no acquisition MCP), hooks, catalog/bundled skills, plugins,
apps or descendants. Inspect the full compiled argv for those settings,
especially disabled discovered MCP identifiers and `agents.enabled=false` /
`features.multi_agent_v2.enabled=false`. Empty compaction overrides inherit
defaults; an empty map is not a universal disable switch.

Shell availability is not permission to use the network or start a client.
No acquisition, live/provider tests, credential-bearing configuration or auth-file reads by the lane,
installs, global configuration, hook/service changes, descendants, other panes,
commits, pushes, GitHub writes or merges are authorized by this template.
The parent owns integration; [AGENTS.md](../../AGENTS.md#working-agreements)
still requires a current-session instruction for merge or auto-merge and prior
approval for destructive operations. Preserve [VISION.md](../../VISION.md)
and unrelated edits. Managed policy, remote configuration and instruction
discovery can qualify requested isolation; inspect actual runtime declarations
separately if a later authorized launch occurs.

## Return and reconsider

Run only the BRIEF's permitted deterministic checks, including `git diff --check`
and relevant link/manifest checks. Report changed files, exact commands and exit
results, source locators, assumptions, unresolved limits, unexpected writes and
rework through the BRIEF-designated report and one-line done/blocked artifact.
Do not contact other panes. The parent reviews the exact diff and accepts,
qualifies, parks or rejects it before integration or publication.

For a later authorized launch, the external launcher's `lane-manifest.json`,
`launch-argv.json` and `launch-receipt.json` record requested settings and launch
state. A `prompted` receipt means submission, not completion. Neither those
records nor a successful compile attest served model/effort or actual tools.

**Revisit before the next real development wave or deeper profile review,
whichever comes first.** Compare outcome, rework and permission friction with
manual launch/no change. No scheduler or enforcement service is installed.
