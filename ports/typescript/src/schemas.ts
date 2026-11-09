import { z } from "zod";
import type {
  Request,
  MaskedSpan,
  HandoffEnvelope,
  SupportTicketOutput,
  AuditEvent,
  IncidentReport,
  IncidentResult,
} from "./types.js";

// Types.ts parity check helpers.
type Expect<T extends true> = T;
type Same<A, B> = A extends B ? (B extends A ? true : false) : false;
type FromZod<S extends z.ZodTypeAny> = z.infer<S>;

const RequestSchema = z
  .object({
    type: z.string().min(1),
    text: z.string(),
    id: z.optional(z.string().min(1)),
  })
  .strict();

const MaskedSpanSchema = z
  .object({
    category: z.string().min(1),
    start: z.number().int().min(0),
    stop: z.number().int().min(0),
    replacement: z.string(),
  })
  .strict();

const SupportTicketOutputSchema = z
  .object({
    label: z.string().min(1),
    label_display: z.string().min(1),
    confidence: z.number().min(0).max(1),
    source: z.enum(["rules", "model_proposal", "abstain"]),
    route: z.string().min(1),
    reply_draft: z.string(),
    citations: z.array(z.string().min(1)),
    rationale: z.optional(z.string()),
    suggest_request_type: z.optional(z.string()),
  })
  .strict();

const HandoffEnvelopeSchema = z
  .object({
    contract_version: z.literal("1.0.0"),
    request_id: z.string().min(1),
    request_type: z.string().min(1),
    plugin_version: z.string(),
    status: z.enum(["awaiting_approval", "handoff"]),
    handoff_reasons: z.array(z.string()),
    route: z.string(),
    masked_text: z.string(),
    masked_categories: z.array(z.string()),
    rule: z.record(z.string(), z.unknown()),
    model: z.record(z.string(), z.unknown()),
    output: SupportTicketOutputSchema,
  })
  .strict();

// Audit events are open objects (additionalProperties: true).
const AuditEventSchema = z
  .object({
    audit_version: z.literal("1.0.0"),
    ts: z.string().min(1),
    event: z.string().min(1),
    request_id: z.string().min(1),
  })
  .passthrough();

const IncidentReportSchema = z
  .object({
    schema_version: z.literal("1.0.0"),
    what: z.string(),
    when: z.string(),
    where: z.string(),
    harm: z.enum(["ingen", "risk", "lindrig", "allvarlig", "okand"]),
    immediate_action: z.string(),
    confidence: z.number().min(0).max(1),
    status: z.enum(["draft", "not_implemented"]),
    route: z.optional(z.string()),
    source_request_id: z.optional(z.string()),
  })
  .strict();

const IncidentResultSchema = z
  .object({
    report: IncidentReportSchema,
    report_errors: z.array(z.string()),
    status: z.string().min(1),
    handoff_reasons: z.array(z.string()),
  })
  .strict();

export {
  RequestSchema,
  MaskedSpanSchema,
  SupportTicketOutputSchema,
  HandoffEnvelopeSchema,
  AuditEventSchema,
  IncidentReportSchema,
  IncidentResultSchema,
};

// Compile-time assertions: hand-written types stay in sync with zod inference.
type _Assert1 = Expect<Same<FromZod<typeof RequestSchema>, Request>>;
type _Assert2 = Expect<Same<FromZod<typeof MaskedSpanSchema>, MaskedSpan>>;
type _Assert3 = Expect<
  Same<FromZod<typeof HandoffEnvelopeSchema>, HandoffEnvelope>
>;
type _Assert4 = Expect<
  Same<FromZod<typeof SupportTicketOutputSchema>, SupportTicketOutput>
>;
type _Assert5 = Expect<Same<FromZod<typeof IncidentReportSchema>, IncidentReport>>;
type _Assert6 = Expect<
  Same<FromZod<typeof IncidentResultSchema>, IncidentResult>
>;
// AuditEvent is a Record intersection; just require assignability.
type _Assert7 = FromZod<typeof AuditEventSchema> extends AuditEvent
  ? true
  : never;
type _Assert8 = Expect<
  Same<FromZod<ReturnType<typeof z.array<typeof AuditEventSchema>>>, AuditEvent[]>
>;

export const AuditEventListSchema = z.array(AuditEventSchema);
