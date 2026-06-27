# Phase Session Quick-Start Reference Card

The full TOKEN EFFICIENCY PROTOCOL lives in CLAUDE.md (always loaded).
This card is the session start command + a cheat sheet. Nothing more.

---

## SESSION START COMMAND (paste this verbatim)

```
Start the next phase using the TOKEN EFFICIENCY PROTOCOL in CLAUDE.md.
Read SESSION TRACKER → produce the Micro-Task List → delegate all execution to Haiku.
Sonnet: plan + diagnose only. Haiku: all files, commands, git, CI, prompts.md.
Phase must complete within 3% session / 0.5% weekly.
```

---

## MODEL ROUTING CHEAT SHEET

| Action | Model |
|---|---|
| Read CLAUDE.md + make Micro-Task List | Sonnet |
| Diagnose CI failure from Haiku's error summary | Sonnet |
| Approve or reject Haiku's result summary | Sonnet |
| Decide architectural approach | Sonnet |
| Write any file (Python, TS, YAML, JSON) | Haiku |
| Edit any file (old_string → new_string) | Haiku |
| Read any file or search codebase | Haiku |
| git add / commit / push / status / diff | Haiku |
| aws cli commands | Haiku |
| npx cdk synth / cdk deploy | Haiku |
| pytest / npm run build / cfn-lint / tfsec | Haiku |
| gh pr create / gh pr checks / gh run view | Haiku |
| Fetch CI failure log (grep errors only) | Haiku |
| Update CLAUDE.md phase checklist [x] | Haiku |
| Append prompts.md audit entry (last step) | Haiku |

---

## BUDGET GUARDRAILS

```
Sonnet turns per phase:  ≤ 5
Haiku tasks per phase:   as many as needed (they're cheap)
Parallel spawns:         always — independent tasks in one message
CI triage cycles:        ≤ 3 before Sonnet does a deeper read
Total per phase:         < 3% of 5-hour session / < 0.5% weekly
```

---

## PARALLEL SPAWN PATTERN (send in one message)

```python
# Group A — independent files, spawn all at once:
Agent(model="haiku", description="Write terraform_parser.py", prompt="...")
Agent(model="haiku", description="Write cloudformation_parser.py", prompt="...")
Agent(model="haiku", description="Write test_terraform_parser.py", prompt="...")

# After Group A confirms done — Group B (depends on A):
Agent(model="haiku", description="Run git commit and push", prompt="...")
```

---

## CI TRIAGE SEQUENCE (exact commands)

```bash
# Haiku runs:
gh run view [run-id] --log-failed | grep -A 10 "ERROR\|FAILED\|ImportError\|assert"
# Haiku reports to Sonnet: error type + file + line (under 50 words)
# Sonnet gives one fix instruction → Haiku implements + pushes
```
