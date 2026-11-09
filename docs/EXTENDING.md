# Extending the copilot with a new request type

The pipeline (`copilot/core/pipeline.py`) is the safety spine. It is the same for every request type:

```
raw text ─▶ mask PII ─▶ plugin.rules ─▶ (≤1) plugin.model_task ─▶ validate ─▶ handoff decision ─▶ audit
              core          plugin            core runs adapter       core          core + plugin       core
```

The core owns masking, the model call, validation, the handoff floor and the audit log. A plugin supplies only domain logic. It can **add** handoff reasons but cannot remove the core's reasons (`patient_data_detected`, `model_output_invalid`, `model_abstained`, `low_confidence`, `empty_input`). Nothing is ever auto-sent. `status` is always `awaiting_approval` or `handoff`, and `copilot/core/approval.py` records the human decision.

There are two ways to add `incident_report` (avvikelse). Both use the same contract: `contracts/incident_report.v1.schema.json`.

## Path (a): a plugin in this app

1. `copilot/plugins/incident_report/plugin.py` is filled in. The package initializer registers it. The plugin detects the harm words, runs one extraction step, and sets `status="draft"`. Every case still forces `incident_always_human`. It does not return `not_implemented`.
   - `rules(masked_text) -> RuleResult`: detect harm words (`fel patient`, `fel dos`, `fall`) and set `route="patientsakerhet"`. Keep `forced_handoff=["incident_always_human"]`.
   - `model_task(...) -> ModelTask`: **one** extraction step that fills what/when/where/harm/immediate_action from the masked text. Its `output_schema` is the contract minus the bookkeeping fields.
   - `build_output(...)`: merge the rules and the model output into a contract-valid dict with `status="draft"`.
   - `handoff_reasons(...)`: for example `harm in {"allvarlig","okand"}`, or an empty `what`.
2. `confidence_threshold` is `0.6`. The old skeleton used `1.01`. Every case still hands off because of `incident_always_human`. If the extracted confidence is below `0.6`, the core also adds `low_confidence`.
3. Tests: copy `tests/test_pipeline.py` patterns and run the plugin with `FakeAdapter` replies.
4. Bridge: a `support_ticket` labelled `journalfel` already carries `output.suggest_request_type = "incident_report"`. The API and CLI accept a follow-up `{"type": "incident_report", ...}` with the **masked** text. The demo page does not expose that button; the 8-minute interview path stays on the four support-ticket examples.

When to choose (a): one deployable, one audit log, shared UI. This is the default for the demo.

## Path (b): a separate, self-contained project chained by contract

The copilot's `run()` result is the **handoff envelope** (`contracts/handoff_envelope.v1.schema.json`). It contains only `masked_text`. The raw text never crosses the boundary. A separate project:

1. Accepts an envelope (stdin/CLI or `POST /incident-reports`).
2. Validates it with the envelope schema and rejects unknown `contract_version`.
3. Returns a JSON object that validates against `contracts/incident_report.v1.schema.json`, with `source_request_id = envelope.request_id`.
4. Keeps its own audit log, keyed by `request_id`, and still requires human approval.

CLI chain (works today; `copilot/chain.py::incident_from_envelope` is the reference consumer, running the incident plugin):

```bash
echo '{"type":"support_ticket","text":"Fel patient fick anteckningen i journalen"}' \
  | python3 -m copilot run --adapter none > envelope.json
python3 -m copilot validate-envelope < envelope.json          # exit 0 = contract-valid
python3 -m copilot incident-from-envelope < envelope.json     # -> {report, report_errors, status, handoff_reasons}
```

Notes on the contract:
- `run()` returns an **envelope**; incident fields sit under `envelope.output`. A standalone service returns a **root** incident document (`incident_report.v1`). `incident_from_envelope` shows the unwrap step.
- The consumer sets `source_request_id = envelope.request_id`. It must carry `envelope.masked_categories` forward. When the input contained a personnummer, the re-submitted text is already masked, so the patient-data flag would otherwise be lost (`upstream_patient_data`).
- Do not pipe an envelope into `copilot run`. It expects `{type, text}`.

HTTP chain: the FastAPI app (`copilot/api.py`) returns the envelope from `POST /requests`. The other service exposes `POST /incident-reports` (body: envelope, response: incident report). The two sides share only the files in `contracts/`. Copy them or vendor them, and bump `schema_version` / `contract_version` on any breaking change.

When to choose (b): a different team or release cycle owns avvikelser, it needs separate data retention (patient-safety reports are kept longer), or you want to show that the safety spine is reusable as a library.

## Rules for any new plugin
- Read only `masked_text`. The plugin never sees raw input.
- Make at most one model step, with a strict output schema. Anything invalid fails closed and hands off.
- Every output field must be in `output_schema` (`additionalProperties: false`).
- Add a synthetic dataset and tests. Use no real data, ever.
