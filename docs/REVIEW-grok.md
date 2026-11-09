# Review (Grok)

Scope: `incident_report` as plugin vs chained project, Swedish mask/rules a reviewer can break live, six-day order. No code changes. Checked with `mask_text`, `classify`, and `pipeline.run` on synthetic text (ref date 2026-11-04).

## 1. Plugin or separate project?

In-process hosting works: `IncidentReportPlugin` registers, `type=incident_report` dispatches, and the skeleton `output` validates against `incident_report.v1`. A second repo can call `validate_envelope` / `validate_incident`. EXTENDING.md treats those as one contract and says the CLI chain works today. It does not.

- Path (a) returns the handoff envelope. Incident fields live under `output`. Envelope `status` is `awaiting_approval|handoff`. Path (b) is a root incident document (`status` `draft|not_implemented`). `validate_incident` on a `run()` result fails.
- `build_output(masked_text, rule, model_output)` has no `request_id`, so the plugin cannot set `source_request_id`. The schema makes that field optional; EXTENDING.md requires it for path (b).
- Envelope `output` and `rule` are open objects. `request_type` is a free string. `suggest_request_type` is only a support-plugin habit, so an envelope consumer has no contracted signal to start an incident.
- Piping an envelope into `python -m copilot run` reads `text`/`type`, ignores `masked_text`/`request_type`, and yields an empty `support_ticket`. `chain.py` only validates. `api.py` has no `POST /incident-reports`.
- Re-submitting `masked_text` drops `patient_data_detected`. The core adds that reason only when this call's categories contain `personnummer` or `identifierare`.
- `approval.decide` returns `reply_draft` or `edited_reply`. An incident has neither; a handoff cannot be approved. `additionalProperties: false` rejects the skeleton's planned `needs_review`. Empty `what` is valid. `schema.py` ignores `$ref`, `oneOf`, and `format`.
- `load_builtin()` imports both plugins by path. There is no entry point. Embedding the spine as a library is a third mode the doc names and does not specify.

## 2. Five tickets to paste

`echo '{"type":"support_ticket","text":"..."}' | python -m copilot run --adapter none`. Hyphenated `19870312-4514`, `070-174 06 05`, and `Anna Svensson` already mask in the fixtures.

1. `Kan inte logga in med SITHS. Anna Svenssons personnummer är 19870312 4514. ssk Maja Holm.` Space defeats the PN pattern (same digits as fixture `pnr-12`), genitive `s` defeats the name list, `ssk` is not a title. Categories `[]`, status `awaiting_approval`, PN and both names sit in `masked_text`. `namn`/`telefon`/`epost` never raise `patient_data_detected`.
2. `Ring (070) 174 06 05 eller 0046-70-174 06 05. Mejl maja.holm(at)example.se. journalnummer JV-2024-9912.` Parentheses, `0046`, `(at)`, and `journalnummer` all remain. Ident prefixes are only patient/dossier/ärende/avdelning/vårdenhet, and the id must be ≥4 characters (`patient nr 12` also survives).
3. `Jag förväxlade två fönster i klienten. Ingen patient inblandad.` Substring `förväxl` → label `journalfel`, route `patientsakerhet`, reasons `patient_safety` and `journal_error_needs_incident_report`, `suggest_request_type=incident_report`.
4. `Anteckningen hamnade på en annan patient och dubbel dos gavs. Patienten fick feldos.` Rules demand the exact phrases `fel patient` and `fel dos`. Result: `ovrigt`, route `forsta_linjen`, no `patient_safety`, no incident suggestion (`--adapter none` still hands off, for `model_abstained`). `avvikelse` scores 2, under `MIN_SCORE` 3. `föll` is not a phrase. `forvaxlade` (no åäö) also misses.
5. `Jag öppnade läkemedelslistan och fick felkod 42.` Pattern `läkemedelslista.*fel` eats `felkod` → `journalfel` plus an incident suggestion, with no safety word in the text.

## 3. Next five steps

1. **Mask floor (day 1).** Spaces and slashes in personnummer, genitives, roles (`ssk`, `namn:`), `0046` and parenthesized phones, obfuscated mail, `journalnummer`/HSA-id. Lock these five texts in as tests. Refuse `awaiting_approval` when a personnummer-shaped token was seen and not masked.
2. **Rules (day 2).** Word boundaries, stop `.*fel` at `felkod`/`felmeddelande`, fold åäö, add `annan patient` / `dubbel dos` / `feldos` / `föll` / `avvikelse`. Keep `patient_safety` off window-mixups and off `allvarlig` plus `krasch`.
3. **One chain contract (day 3).** Document unwrap vs root document, pass `request_id` into the plugin, put the bridge field on the envelope, carry `masked_categories` across re-submit, `minLength` on `what`, fix the EXTENDING.md CLI.
4. **Fill path (a) (days 4–5).** One extraction task, bookkeeping fields kept out of the model schema, `incident_always_human`, empty `what` hands off. Approval stores an incident edit.
5. **Path (b) that reads an envelope (day 6).** Stdin → envelope check → incident JSON and a separate audit line. RAG drafter and a full JSON Schema parser wait until a pasted ticket survives steps 1–2.
