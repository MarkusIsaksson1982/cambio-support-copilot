# Scope freeze — 5 Nov 2026 (demo for 11 Nov)

All data synthetic. Supersedes the provisional leanings in [SCOPE-DECISIONS.md](SCOPE-DECISIONS.md) where they conflict.

## Locked (Markus, 5 Nov)
- **Live failure case:** patient data → forced human handoff (hero ticket `G-001` in `data/gap_tickets_2026-11-05.jsonl`, test number 19121212-1212). RAG fail-closed stays in the product but is not the live moment.
- **Backup if live breaks:** recording **plus** offline report.
- **Presentation in English, tickets in Swedish.** Swedish one-page UI: paste → masked → draft → approve. The page is `ui/index.html` at `GET /`, adapter `none`, with an inspelat mode over `ui/examples.json`.

## Users
- Primary: 1st/2nd-line support staff at a healthcare-software vendor handling customer tickets (ssk, usk, systemförvaltare, MAS write them).
- Secondary: the reviewer who approves, edits, rejects or takes over a draft.

## Non-goals
- No auto-send, ever. No clinical advice. No reading or changing a real journal.
- No real patient data; no full FHIR/openEHR conformance claim (adapter emits `mapping_status` / `needs_review`).
- Incident plugin logic and retrieval over the 11 synthetic knowledge-base documents are in the product (7 Nov). An incident always hands off. Friday rules and the golden-label pass are closed (6 Nov).

## Schemas
- Request in: `{"type": "support_ticket"|"incident_report", "text": str}`.
- Envelope out: `contracts/handoff_envelope.v1` (status `handoff` | `awaiting_approval`, `handoff_reasons`, `masked_text`, `route`, `rule`, `model`, `output`).
- Incident: `contracts/incident_report.v1`.
- Eval tickets: `data/support_tickets.jsonl` (`id, text, expected_label, expected_status`); `data/gap_tickets_2026-11-05.jsonl` adds `category, expected_route, contains_pii, needs_human, scenario` from the merged synthetic corpus used to build the gap set.

## Handoff rules
See README "Handoff rules". Invariant tested on the gap set: `needs_human=true ⇒ status=handoff`. `G-003` closed Fri 6 Nov: Luhn-invalid samordningsnummer in patient/journal context forces `patient_data_detected` without changing Luhn-strict masking.
