# Cross-language ports (Python → TypeScript / C# / Java + React)

Goal: show the demo's data structures move to the languages Cambio uses, and how AI-assisted
translation was done **and verified** rather than trusted.

## Source of truth
`ports/schemas/*.json` (JSON Schema 2020-12). The envelope and incident schemas reference the
existing `contracts/` so nothing diverges.

| Schema | What it is |
|---|---|
| `request.v1` | ticket/request input (`type`, `text`, optional id) |
| `masked_span.v1` | one masked identifier (category, start, stop, replacement) |
| `handoff_envelope.v1` | the decision: status, handoff_reasons, route, masked_text, rule, model, output |
| `audit_event.v1` | one append-only audit line (`audit_version`, `ts`, `event`, `request_id`, extras) |
| `incident_report.v1` | incident contract (chain consumer output) |

## Shared fixtures
`ports/gen_fixtures.py` runs the **real Python pipeline** (Fake/None adapters) and dumps
`ports/fixtures/*.json`. Every port must deserialize each fixture into typed objects,
re-serialize, and compare semantically equal JSON. Python validates the fixtures against the
schemas (`tests/test_ports_fixtures.py`).

## Ports
| Port | Style | Test | Status (box, 2026-11-04) |
|---|---|---|---|
| TypeScript `ports/typescript` | hand-shaped types + zod (`.strict()` where `additionalProperties:false`) | `npm test` (node:test, 9 tests incl. negative strictness + React SSR render) | 9/9 pass |
| React `ports/typescript/src/TicketDecision.tsx` | component: masked text, label, confidence, route, status, reasons, draft, Approve/Reject | rendered with `react-dom/server` from the envelope fixture | pass |
| C# `ports/csharp` | .NET 8 `record`s + System.Text.Json (`JsonPropertyName` snake_case) | `dotnet run --project Cambio.Ports.RoundTrip -- ../fixtures` | pass |
| Java `ports/java` | Java 21 `record`s + Jackson | `mvn compile exec:java` | pass |

Run all: `ports/run_all.sh` (skips a language whose toolchain is missing).

## How the AI translation was done
1. **Codex** (`codex exec`, one brief) read `pipeline.py`, `plugin.py`, `audit.py`, `contracts/`
   and wrote the schemas, the fixture generator, and the C# and Java ports. It ran the builds itself.
2. **OpenCode** (free model `opencode/glm-5.3-flash-free`, stdin closed) wrote the TypeScript/zod
   types and the React component from the schemas, fixtures and the C# port.
3. **Verification, not trust**: the orchestrator re-ran every toolchain independently, regenerated
   fixtures after a Python masking change, and re-ran all round trips (`run_all.sh`). The fixtures
   come from Python, so a port that drops or renames a field fails the round trip.

## Lessons / adaptation points
- Open-ended dicts (`rule`, `model`, audit extras) map to `Dictionary<string, JsonElement>` /
  `Map<String, JsonNode>` / `z.record` + passthrough; they are the weakest typed parts.
- Optional fields: Python omits keys; C# needs `JsonIgnoreCondition.WhenWritingNull`, Jackson
  `@JsonInclude(NON_NULL)`, zod `.optional()` – otherwise round trips add `null`s.
- Numbers: `confidence` 1 vs 1.0 – compare JSON semantically, not textually.
