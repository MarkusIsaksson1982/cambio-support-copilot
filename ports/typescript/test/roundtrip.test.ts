import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import {
  RequestSchema,
  MaskedSpanSchema,
  HandoffEnvelopeSchema,
  AuditEventListSchema,
  IncidentReportSchema,
  IncidentResultSchema,
} from "../src/schemas.js";
import type {
  Request,
  MaskedSpan,
  HandoffEnvelope,
  AuditEvent,
  IncidentReport,
  IncidentResult,
} from "../src/types.js";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, "..", "..", "..", "..", "ports", "fixtures");
const load = (name: string) =>
  JSON.parse(readFileSync(join(fixtures, name), "utf8"));

test("request fixture roundtrips through strict schema", () => {
  const original = load("request.json") as Request;
  const parsed = RequestSchema.parse(original);
  assert.deepEqual(parsed, original);
  assert.deepEqual(JSON.parse(JSON.stringify(parsed)), original);
});

test("masked_span fixture roundtrips through strict schema", () => {
  const original = load("masked_span.json") as MaskedSpan;
  const parsed = MaskedSpanSchema.parse(original);
  assert.deepEqual(parsed, original);
});

test("handoff_envelope fixture roundtrips through strict schema", () => {
  const original = load("handoff_envelope.json") as HandoffEnvelope;
  const parsed = HandoffEnvelopeSchema.parse(original);
  assert.deepEqual(JSON.parse(JSON.stringify(parsed)), original);
});

test("incident_report fixture roundtrips through strict schema", () => {
  const original = load("incident_report.json") as IncidentReport;
  const parsed = IncidentReportSchema.parse(original);
  assert.deepEqual(JSON.parse(JSON.stringify(parsed)), original);
});

test("incident_result fixture roundtrips through strict schema", () => {
  const original = load("incident_result.json") as IncidentResult;
  const parsed = IncidentResultSchema.parse(original);
  assert.deepEqual(JSON.parse(JSON.stringify(parsed)), original);
});

test("audit_events fixture roundtrips through passthrough schema", () => {
  const original = load("audit_events.json") as AuditEvent[];
  const parsed = AuditEventListSchema.parse(original);
  assert.deepEqual(JSON.parse(JSON.stringify(parsed)), original);
});

test("audit_events keep their open (additional) fields after parse", () => {
  const original = load("audit_events.json") as AuditEvent[];
  const parsed = AuditEventListSchema.parse(original);
  assert.equal(parsed[1].label, "inloggning");
  assert.equal(parsed[2].status, "awaiting_approval");
});

test("strict schemas reject unknown properties (additionalProperties false)", () => {
  const envelope = load("handoff_envelope.json") as HandoffEnvelope;
  assert.throws(() =>
    HandoffEnvelopeSchema.parse({ ...envelope, extra: true })
  );
  assert.throws(() => RequestSchema.parse({ type: "x", text: "y", nope: 1 }));
});
