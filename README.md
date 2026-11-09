# cambio-support-copilot (demo core)

A Swedish **support copilot** for healthcare-software support staff. It is the interview demo for the Cambio Associate AI Engineer interview (2026-11-11). **All data is synthetic.** Nothing is ever auto-sent.

```
raw ticket ─▶ mask PII ─▶ rule-first route ─▶ ≤1 narrow model step ─▶ validate (fail closed) ─▶ human approval / handoff ─▶ audit (JSONL, masked)
```

Request types are **plugins** (`copilot/plugins/*`). `support_ticket` and `incident_report` (avvikelse) are both implemented. An incident always hands off. See [docs/EXTENDING.md](docs/EXTENDING.md).

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q                                 # 137 passed, 10 xfailed (Luhn-invalid personnummer; still a handoff)
.venv/bin/python -m copilot eval                              # offline pack, docs/EVAL-2026-11-08.md
.venv/bin/uvicorn copilot.api:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000/ . The page uses adapter `none`, the same offline path as the evaluation pack. Use `python3` if `python` is not on your PATH.

CLI examples (optional; the page above is the interview path):

```bash
echo '{"type":"support_ticket","text":"Kan inte logga in med SITHS. /Anna Svensson 070-174 06 07"}' \
  | .venv/bin/python -m copilot run --adapter none
echo '{"type":"support_ticket","text":"Fel patient fick anteckningen, pnr 19870312-4514"}' \
  | .venv/bin/python -m copilot run | .venv/bin/python -m copilot incident-from-envelope
```

`--adapter fake` remains available on the CLI as a deterministic model stub. It is not used by the demo page.

## Layout
| path | what |
|---|---|
| `copilot/core/masking.py` | personnummer (10/12 digits, Luhn, samordningsnummer), orgnr, phone, e-mail, ids, names. Ported from **arende-triage** |
| `copilot/core/pipeline.py` | the safety spine. Fail-closed on plugin/adapter errors, prompt re-mask guard, envelope validation |
| `copilot/core/plugin.py` | `RequestPlugin` protocol + registry (`rules`, `model_task`, `build_output`, `handoff_reasons`) |
| `copilot/core/adapters.py` | model adapters: `none`, `fake` (deterministic), `local` (Ollama), `opencode` (stdin closed). Tolerant JSON parse (subset of **llm-json-fixer**) |
| `copilot/core/schema.py` | stdlib JSON-schema subset validator (from arende-triage) |
| `copilot/core/approval.py` | human decision: approve / edit / reject / take_over. A handoff cannot be approved as-is |
| `copilot/core/audit.py` | append-only JSONL. Re-masked, stores the input hash only |
| `copilot/plugins/support_ticket/` | Swedish rules (inloggning, behörighet, journalfel, bugg, instruktion, övrigt), routes, `RetrievalDrafter` |
| `copilot/plugins/incident_report/` | one extraction step, always `incident_always_human`, nothing is sent |
| `ui/` | Swedish demo page, frozen examples, offline eval sidebar |
| `copilot/chain.py` | contract validation + `incident_from_envelope` (reference path-b consumer) |
| `contracts/` | `handoff_envelope.v1`, `incident_report.v1` JSON schemas |
| `data/` | 30 synthetic tickets, 14 Thu 5 Nov gap tickets (patient-data handoff, incident, abstain, support) + arende-triage identifier fixtures |
| `docs/` | [SCOPE.md](docs/SCOPE.md) (frozen 5 Nov: users, non-goals, schemas, handoff rules), EXTENDING.md, REVIEW-codex.md, REVIEW-grok.md |

## Handoff rules (never auto-send)
A case always goes to a human (`status: handoff`) when any of these hold: a personnummer or id is detected, patient-safety wording appears (`fel patient`, `annan patient`, `fel dos`, `dubbel dos`, …), the label is `journalfel` (it suggests an `incident_report`), the model abstained or returned invalid output, the label came from a model proposal, confidence is low, there is no grounded draft, or a plugin or adapter error occurred. Otherwise the status is `awaiting_approval`, and a human still has to approve the draft.

## How this was built
I directed this demo through AI-assisted coding and agentic workflows with Codex, OpenCode, Grok Build, Cursor and local models, with Grok Bot orchestrating. I set the scope, designed the safety gates and evaluations, reviewed diffs, decided what to keep or reject, and verified the test suite and the four frozen examples. I did not hand-write most of the code.

| tool | what it contributed, under that review |
|---|---|
| **Grok Bot** | architecture, core pipeline/plugin API/adapters/audit/approval, support_ticket plugin, incident plugin, contracts, EXTENDING.md, chain consumer, adversarial fixes after review, API tests, README |
| **OpenCode** `nemotron-3.5-lightning-free` | `data/support_tickets.jsonl` (30 tickets), `tests/test_masking.py`, `test_pipeline.py`, `test_approval.py`, `test_dataset.py` |
| **Codex** | design review [docs/REVIEW-codex.md](docs/REVIEW-codex.md). Fail-closed hardening of `pipeline.py` (hook/adapter exceptions → handoff, prompt re-mask guard, model-output re-mask, envelope validation) + `tests/test_fail_closed.py` |
| **Grok Build** | [docs/REVIEW-grok.md](docs/REVIEW-grok.md): contract gaps for path (b), 5 live demo-breaking tickets, next steps. Those findings drove the space-separated personnummer fix, the rule fixes and `tests/test_chain_and_adversarial.py` |
| **Cursor** | A comparable coding harness used alongside the others when directing and reviewing work |
| **Local models** (Ollama) | Edge-case discovery; recorded replies are replayed as offline fixtures in `tests/fixtures/` |

Prompts sent to outside models were checked first so they contained no personal data or tokens.

## What landed on 7 Nov
- Reply drafting: `RetrievalDrafter` over `data/kb.json` (11 synthetic docs). A miss returns no draft, which hands off. `TemplateDrafter` is still there for the old fixed citations.
- `incident_report`: harm words (`fel patient`, `fel dos`, whole-word `fall`), one extraction step, `status=draft`, and `incident_always_human` on every case. Nothing is sent.

## What landed on 9 Nov
- Bare Swedish given-name + surname pairs in patient context are masked as `[namn-maskat]`. The matcher combines role cues (`patient`, `testpatienten`, `Exempelpatient:`), a name sitting immediately before a personnummer-shaped token, and a given-name gazetteer. On G-001 both the Skatteverket test number and the synthetic name are masked.
- Staff slash-signatures such as `/Mikael` and the single-letter placeholder `patient X` are also masked. A bare given name with no slash, title or surname (for example `Hej Mikael,`) can still appear. Masking stays Luhn-strict: an invalid number is not rewritten, but a date-plausible shape in patient context still forces a handoff.
- Shared port fixtures were regenerated from the live pipeline. `incident_report` now shows `status: draft` (the plugin has been implemented since 7 Nov). The live plugin never returns `not_implemented`.

## Demo page
`ui/index.html` is served at `/`. Paste a ticket, read the masked text, the draft and the citation, then approve, reject or take over. Inspelat mode shows `ui/examples.json` and does not send a decision. Godkänn stays disabled unless the case is `awaiting_approval`. The sidebar repeats `docs/EVAL-2026-11-08.md` and is not a live-model score.

Citation strings such as `opencode-deepseek-v4.1-flash-free:KB-001` are ids of synthetic knowledge-base articles, named after the worker that drafted that article. They are not a live model call during the demo.

The page disables "Redigera och skicka" when `patient_data_detected` is set. The API still allows `edit` on a handoff; that is the reviewed escape hatch, not the button for G-001.

A silent recording of the page (G-001 handoff with the name and personnummer masked, the SITHS approval, the rejected print-runbook citation, and the offline sidebar) is at [docs/cambio-demo-recording.mp4](docs/cambio-demo-recording.mp4). A short one-pager is at [docs/one-pager.pdf](docs/one-pager.pdf).

## Known gaps / roadmap

These are deliberate demo limits, not unfinished buttons on the interview page.

- **Luhn-invalid personnummer.** Masking stays Luhn-strict so G-003 can show the gap: `19850372-6614` remains visible and the case still hands off (`patient_data_detected`). The 10 xfailed tests are this class.
- **Bare isolated given names.** A name with no slash signature, title/role cue or surname (for example `Hej Mikael,`) is left visible. Slash signatures (`/Mikael`) and the placeholder `patient X` are masked.
- **No incident form on the demo page.** The `incident_report` plugin is live on the API and CLI (`type=incident_report`, or `python -m copilot incident-from-envelope`). The four page buttons stay `support_ticket` so the 8-minute path is unchanged.
- **API edit-on-handoff.** The page disables "Redigera och skicka" when `patient_data_detected` is set. The API still accepts `edit` on a handoff if `edited_reply` is supplied; that is the reviewed escape hatch.
- **In-memory audit and results.** `RESULTS` and `AUDIT` on the demo API live in the process and disappear when it stops. `AuditLog` can append JSONL when given a path; the page does not do that. A second decision on the same id is blocked in the UI, not in the API.
- **`sent` is local.** Approve and edit record a local audited label. There is no ticketing integration and nothing is delivered outbound.
- **No FHIR/openEHR mapping adapter.** Earlier notes mentioned an adapter that would emit `mapping_status` / `needs_review`. That adapter is not implemented, and this demo makes no conformance claim.
- **Language ports are contract round-trips.** `ports/csharp`, `ports/java` and `ports/typescript` deserialize and re-serialize the shared JSON fixtures. They do not reimplement the Python pipeline. The incident schema still allows `status: not_implemented` for older consumers; the live plugin emits `draft`.
- **Retrieval is token overlap**, with a light Swedish stem, not a neural ranker. ticket-008 is the known false friend (print-runbook citation). The hit threshold is frozen for interview week.
- **Live-model variability.** `docs/EVAL-2026-11-08.md` repeats the offline path three times and does not call a model. A separate three-repeat probe is in `docs/LIVE-PROBE-2026-11-09.md`. It is not that score. The demo page stays on adapter `none`. `--adapter fake` remains a CLI-only deterministic stub.
