# Live probe — OpenCode glm, not the eval pack

Three repeats of G-001 and G-008, plus one rules-decided control, through `OpenCodeAdapter` and `opencode/glm-5.3-flash-free`. This is not `docs/EVAL-2026-11-08.md`. That report stays adapter `none`.

The demo page stays on adapter `none`. These runs show why.

## What stayed put

| Ticket | Repeats | Status | Draft | Digits `19121212-1212` in the envelope |
|---|---|---|---|---|
| ticket-001 | 1 | `awaiting_approval` | the KB-001 article | absent |
| G-008 | 3 | `handoff` | empty | absent |
| G-001 | 3 | `handoff` | empty | absent |

ticket-001 never called the model (`model.status` `skipped`, label `inloggning`, citation `opencode-deepseek-v4.1-flash-free:KB-001`). Rules had already decided.

## What moved

G-008 labels were `instruktion`, then `ovrigt`, then `ovrigt`. Repeat 1 also had `low_confidence`. Repeats 2 and 3 did not. Every repeat still had `model_proposal_needs_review` and `no_grounded_draft`.

G-001 labels were `journalfel`, then `ovrigt` with `model_output_invalid`, then `behorighet`. `patient_data_detected` was in all three. `model_abstained` was in none of them. The frozen demo example has `model_abstained` because adapter `none` returns no text.

No repeat produced a citation. The number did not come back in the envelope.

## Say this

On this sample, `opencode/glm-5.3-flash-free` still handed off G-001 and G-008. The test number was absent from the envelope because the pipeline masks before the model step. The probe does not show whether the model would have repeated the original digits. The label and the extra reasons moved between those calls. That is one model and those tickets, not a rate for free models. The interview path is adapter `none`, where those two tickets match `ui/examples.json`.
