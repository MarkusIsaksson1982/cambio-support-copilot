// Type definitions mirroring ports/schemas and ports/contracts JSON Schema
// files exactly (snake_case field names preserved).

export interface Request {
  type: string;
  text: string;
  id?: string;
}

export interface MaskedSpan {
  category: string;
  start: number;
  stop: number;
  replacement: string;
}

export type Harm = "ingen" | "risk" | "lindrig" | "allvarlig" | "okand";

export type IncidentReportStatus = "draft" | "not_implemented";

export interface IncidentReport {
  schema_version: "1.0.0";
  what: string;
  when: string;
  where: string;
  harm: Harm;
  immediate_action: string;
  confidence: number;
  status: IncidentReportStatus;
  route?: string;
  source_request_id?: string;
}

export type HandoffStatus = "awaiting_approval" | "handoff";

export type SupportTicketOutputSource =
  | "rules"
  | "model_proposal"
  | "abstain";

export interface SupportTicketOutput {
  label: string;
  label_display: string;
  confidence: number;
  source: SupportTicketOutputSource;
  route: string;
  reply_draft: string;
  citations: string[];
  rationale?: string;
  suggest_request_type?: string;
}

export interface HandoffEnvelope {
  contract_version: "1.0.0";
  request_id: string;
  request_type: string;
  plugin_version: string;
  status: HandoffStatus;
  handoff_reasons: string[];
  route: string;
  masked_text: string;
  masked_categories: string[];
  rule: Record<string, unknown>;
  model: Record<string, unknown>;
  output: SupportTicketOutput;
}

export type AuditEvent = {
  audit_version: "1.0.0";
  ts: string;
  event: string;
  request_id: string;
} & Record<string, unknown>;

export interface IncidentResult {
  report: IncidentReport;
  report_errors: string[];
  status: string;
  handoff_reasons: string[];
}
