# Scope decisions — PROVISIONAL

Source: Lo · Cambio round 1 (`lo-cambio-2026-11-04T2049.json`, level 1, weight 0.25), 2026-11-04.
**Provisional 1/3 picks — leanings, not strong decisions.** Markus: first test round, still iterating.

## Leanings
- **Live run:** full 42 tickets offline, show the report.
- **Demo language:** English presentation, Swedish tickets.
- **Backup:** 3-minute recording.
- **UI:** Swedish one-page web UI — paste → masked → draft → approve.
- **Live failure case:** ungrounded RAG answer → fail closed (see `tests/test_rag_abstain_fixtures.py`).

## Skipped / undecided
- Headline metric
- Paid session
- Microsoft/Teams angle
- Incident plugin vs separate project

## Comments
- First test round; still iterating.
- Talking points deferred tonight.
- Welcome to test local models between rounds.

---

# Round 2 — PROVISIONAL

Source: Lo · Cambio round 2 (`lo-cambio-2026-11-04T2114.json`, level 2, weight 0.5), 2026-11-04.
Still leanings, not decisions. Weighted tally = sum of round weights per option (R1 0.25, R2 0.5).

## New leanings
- **FHIR:** adapter that emits `mapping_status` / `needs_review` (incident → AdverseEvent, ticket → Task); no claim of full conformance.
- **RAG:** ~8 fake internal docs in a local vector index.
- **Incident/avvikelse draft:** second intent on the same gate (plugin), not a separate project.
- **UI:** Swedish one-page UI again — now picked in 2 sessions (0.75).

## Open conflicts (round 1 vs round 2)
| Question | Round 1 (0.25) | Round 2 (0.5) | Weighted tally | Status |
|---|---|---|---|---|
| Backup if live demo breaks | 3-min recording | Both (recording + offline report) | both 0.5 · recording 0.25 | **open** — tiebreak card in next round |
| Failure case shown LIVE | Ungrounded RAG → fail closed | Patient data → forced human handoff | patient-handoff 0.5 · RAG fail-closed 0.25 | **open** — tiebreak card in next round |

## Edge-case ranking (net score, round 2)
1. **2** — `med-incident`: llama labels medication tickets as incidents (5/5)
1. **2** — `invented-span`: qwen2.5:3b invents the PII span "22-4821", not in the text
1. **2** — `wrong-label`: schema-valid but wrong label (rated *high* as a live moment — why approval exists)
4. **1** — `missing-key`: `{"label":"ovrigt","confidence":0.8}` (3b ×11)
5. **−1** — `luhn`
6. **−2** — `misspelled-key`, `staff-fp`

The top three are now offline replay fixtures: `tests/fixtures/top_edge_cases.json`, `tests/test_top_edge_cases.py`.

## Abbreviations
"Don't know" on all 6 cards (us, KAVA, ADL, inf, ca, UL). The game now shows the expansion + an example after each answer; "Don't know" stays a valid answer.

## Ingesting typed overrides (Lo · Cambio v=c4+, 2026-11-05)
Lo exports (`lo-cambio.export.v1`) can now include optional `manualReply` / `overridden: true` fields on records, plus a `manual_replies[]` list. Treat a `manualReply` as the player's stated preference or judgment. It takes precedence over the picked choice, and any picked choice (`selected_*`) is only context. Text-only replies (`selected_choice: null`) appear only in `manual_replies[]`. Review them by hand when applying the usual level weighting. Never discard them.

## Lo · Cambio level 4 (2026-11-05)
Level 4 is playable and fills `cambio.level45.records` with `ticket_edit.v1`, `bulk_label.v1`, `abbreviation_verification.v1` (optional `source_url`), and `pii_span_annotation.v1`. Level 5 (`new_ticket.v1` from scratch) is still coming later. Treat level-4 records as immediate-review data-creation output (weight ×1.5 when performance ≥80%).

## Lo · Cambio round 2026-11-05 18:09 (data level 4, weight ×1.5, perf 0.959, scope/talking/edge only, no level-4 records)
These picks add to the earlier leanings. They don't replace them.
- UI: Swedish one-page web UI (paste → masked → draft → approve)
- FHIR depth: both mappings, each with `mapping_status` / `needs_review`
- Language: English UI/explanations with Swedish tickets
- RAG: ~8 fake internal docs, local vector index
- **Paid spend (typed override):** "Rather spend Codex and/or Grok in Build spend in relation to the relevance rating from Data Creation rounds". Tie Codex/Build spend to how relevant level-4 data-creation rounds rate the work, rather than earmarking spend per task.
- Edge: featured cases are wrong-label, luhn, missing-key, invented route `report_request`, and med-incident. invented-span is now only a brief mention in multi-model summaries.
