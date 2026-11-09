import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import { renderToString } from "react-dom/server";
import React from "react";
import TicketDecision from "../src/TicketDecision.js";
import { HandoffEnvelopeSchema } from "../src/schemas.js";
import type { HandoffEnvelope } from "../src/types.js";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, "..", "..", "..", "..", "ports", "fixtures");
const envelope = HandoffEnvelopeSchema.parse(
  JSON.parse(readFileSync(join(fixtures, "handoff_envelope.json"), "utf8"))
) as HandoffEnvelope;

test("TicketDecision renders handoff_envelope content server-side", () => {
  let approved = false;
  let rejected = false;
  const html = renderToString(
    React.createElement(TicketDecision, {
      envelope,
      onApprove: () => {
        approved = true;
      },
      onReject: () => {
        rejected = true;
      },
    })
  );
  assert.match(html, new RegExp(envelope.masked_text));
  assert.match(html, /Inloggning \/ SITHS/);
  assert.match(html, /0\.85/);
  assert.match(html, /forsta_linjen/);
  assert.match(html, /awaiting_approval/);
  assert.match(html, new RegExp(envelope.output.reply_draft.slice(0, 20)));
  assert.match(html, /Approve/);
  assert.match(html, /Reject/);
  assert.equal(approved, false);
  assert.equal(rejected, false);
});
