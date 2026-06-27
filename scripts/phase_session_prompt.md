# Phase Session Prompt — Token-Optimized Two-Tier Workflow
## Paste this at the start of every new phase session

---

## SESSION BOOTSTRAP (Sonnet does this — ~1% budget)

You are the Lead Architect (Sonnet 4.6). Before writing a single line of code:

1. Read CLAUDE.md SESSION TRACKER — identify current phase and exact next step
2. Read PHASE STATUS — confirm which items are [ ] vs [x]
3. Produce a MICRO-TASK LIST (see format below) — this is your only planning output
4. Do NOT read any other files during planning. Do NOT write any code yourself.
5. Execute the micro-task list using the two-tier model strategy below.

---

## TWO-TIER MODEL STRATEGY

### Tier 1 — Haiku 4.5 (Worker) handles:
- Writing new Python files (given exact function signatures + logic spec)
- Writing new TypeScript CDK files (given exact construct list + props)
- Writing test files (given exact test names + assert conditions)
- Writing YAML/JSON config files (given exact schema)
- Simple edits to existing files (given old_string + new_string explicitly)

### Tier 2 — Sonnet 4.6 (You) handles:
- Reading CLAUDE.md at session start (once only)
- Producing the micro-task list
- Verifying Haiku output (spot-check 1-2 key lines per file — not full re-read)
- Debugging CI failures (read only the failed log section, not full files)
- Architectural decisions and edge cases
- Updating CLAUDE.md + prompts.md (mandatory last step)

---

## MICRO-TASK LIST FORMAT

After reading CLAUDE.md, produce this exact structure. Nothing else.

```
PHASE N — [Phase Name]
Budget: 3% session / 0.5% weekly
Tasks: [count]

HAIKU TASKS (spawn in parallel where independent):
  H1. CREATE scanner/src/parsers/terraform_parser.py
      - Function: parse(content: bytes) -> dict[str, dict[str, dict]]
      - Uses: python-hcl2, hcl2.load(io.StringIO(content.decode()))
      - Returns: {resource_type: {resource_name: {attr: value}}}
      - Edge cases: empty file returns {}, malformed raises ValueError

  H2. CREATE scanner/src/parsers/cloudformation_parser.py
      - Function: parse(content: bytes) -> dict[str, dict[str, dict]]
      - Uses: cfn_flip.to_dict(content.decode())
      - Key: extract["Resources"] only
      - Returns: {ResourceType: {LogicalId: Properties}}

  H3. CREATE scanner/tests/test_terraform_parser.py
      - 5 tests: test_valid_tf, test_empty_tf, test_nested_resource,
        test_multi_resource, test_malformed_raises
      - No mocking needed — pure unit tests on bytes input

SONNET TASKS (sequential, you do these):
  S1. Run: npx cdk synth --context env=dev → verify zero warnings
  S2. Watch CI on PR → debug any failures (read log only, not source files)
  S3. Update CLAUDE.md phase status + SESSION TRACKER
  S4. Append prompts.md entry (LAST step)
```

---

## HAIKU SPAWN TEMPLATE

When spawning a Haiku worker, use this exact Agent call pattern:

```
Agent(
  subagent_type="claude",
  model="haiku",
  description="Write [filename]",
  prompt="""
Write the file [absolute/path/to/file.py].

EXACT REQUIREMENTS (implement precisely — no extras, no refactoring):
[paste the H-task spec here verbatim]

PROJECT RULES (mandatory):
- Python: structured logging (logger.info(json.dumps({...}))), no print()
- Python: env vars via os.environ["VAR_NAME"] at module top (KeyError = fail fast)
- TypeScript CDK: const env = this.node.tryGetContext('env') ?? 'dev'
- TypeScript CDK: const removalPolicy = cdk.RemovalPolicy.DESTROY (always, no condition)
- No comments unless the WHY is non-obvious
- No error handling for impossible cases
- Match imports exactly to what's in scanner/requirements.txt

Write the complete file content. Nothing else — no explanation, no summary.
"""
)
```

---

## TOKEN BUDGET GUARDRAILS

### Per-turn rules (Sonnet enforces these on itself):
- Read a file ONCE. Never re-read after editing.
- Never read files "to understand context" — only read when you need the exact content.
- Spawn Haiku workers in PARALLEL for independent tasks (H1+H2+H3 in one message).
- Verify Haiku output by reading only the first 20 lines + the key function — not the whole file.
- CI debugging: read only the ERROR section of the log (use grep/tail in the bash command).
- Never run `cdk synth` more than once per phase unless a CDK file changed.

### Phase budget targets:
```
Planning (Sonnet reads CLAUDE.md + produces micro-task list): ~0.3% session
Haiku workers (file creation, parallel):                      ~1.0% session
Sonnet verification (spot-checks, not full reads):            ~0.5% session
CI debugging (if needed, log sections only):                  ~0.7% session
CLAUDE.md + prompts.md update (Sonnet):                       ~0.2% session
Buffer:                                                        ~0.3% session
─────────────────────────────────────────────────────────────────────────────
TOTAL TARGET per phase:                                        ~3.0% session
                                                               ~0.5% weekly
```

---

## VERIFICATION CHECKLIST (Sonnet runs after all Haiku tasks complete)

Before creating the PR:
```
[ ] npx cdk synth --context env=dev → 0 errors, 0 warnings
[ ] pytest [changed dirs only] -v --ignore=*/tests/fixtures → all pass
[ ] git diff --stat → only expected files changed
[ ] CLAUDE.md phase checklist updated [x]
[ ] prompts.md entry appended (LAST)
```

---

## WHAT HAIKU MUST NEVER DO

- Read CLAUDE.md (it doesn't need project context — Sonnet gives it everything)
- Make architectural decisions (strict file spec only)
- Create files not in the micro-task list
- Add features beyond the spec ("while I'm here, I'll also add...")
- Spawn further subagents

---

## SESSION START COMMAND

Paste this at the very beginning of a new phase session:

> "Start the next phase. Use the two-tier workflow from scripts/phase_session_prompt.md.
>  Read CLAUDE.md SESSION TRACKER, produce the micro-task list, then execute it.
>  Haiku writes files, you verify and handle CI. Update prompts.md last."
