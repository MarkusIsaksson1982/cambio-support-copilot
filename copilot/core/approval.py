"""Human-in-the-loop: nothing leaves the copilot without an explicit, audited human decision."""
from __future__ import annotations

from datetime import datetime

from copilot.core.audit import AuditLog
from copilot.core.masking import mask_note

DECISIONS = ("approve", "edit", "reject", "take_over")


def decide(result: dict, reviewer: str, decision: str, audit: AuditLog,
           note: str = "", edited_reply: str | None = None,
           reviewed_at: str | None = None) -> dict:
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer is required")
    if reviewed_at:
        datetime.fromisoformat(reviewed_at)  # raises on non-ISO timestamps
    if decision == "approve" and result["status"] != "awaiting_approval":
        raise PermissionError("a handoff case cannot be approved as-is; use edit or take_over")
    if decision == "edit" and not edited_reply:
        raise ValueError("edit requires edited_reply")
    final = {"approve": "sent", "edit": "sent", "reject": "rejected",
             "take_over": "human_owned"}[decision]
    rec = audit.write("human_decision", result["request_id"], reviewer=reviewer,
                      decision=decision, final_state=final, note_masked=mask_note(note),
                      edited=bool(edited_reply), reviewed_at=reviewed_at)
    return {"request_id": result["request_id"], "final_state": final,
            "reply": mask_note(edited_reply) if edited_reply else
            (mask_note(result.get("output", {}).get("reply_draft")) if final == "sent" else None),
            "audit": rec}
