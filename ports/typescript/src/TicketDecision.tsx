import React from "react";
import type { HandoffEnvelope } from "./types.js";

export interface TicketDecisionProps {
  envelope: HandoffEnvelope;
  onApprove?: (envelope: HandoffEnvelope) => void;
  onReject?: (envelope: HandoffEnvelope) => void;
}

export default function TicketDecision({
  envelope,
  onApprove,
  onReject,
}: TicketDecisionProps) {
  const { output } = envelope;
  return (
    <article className="ticket-decision">
      <pre className="masked_text">{envelope.masked_text}</pre>
      <p className="status">{envelope.status}</p>
      <p className="label_display">{output.label_display}</p>
      <p className="confidence">{output.confidence}</p>
      <p className="route">{envelope.route}</p>
      <ul className="handoff_reasons">
        {envelope.handoff_reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <blockquote className="reply_draft">{output.reply_draft}</blockquote>
      <button type="button" className="approve" onClick={() => onApprove?.(envelope)}>
        Approve
      </button>
      <button type="button" className="reject" onClick={() => onReject?.(envelope)}>
        Reject
      </button>
    </article>
  );
}
