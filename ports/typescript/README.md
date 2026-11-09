# ports/typescript

TypeScript port of the cambio copilot boundary contracts, mirroring
`ports/schemas/*.json` and `ports/fixtures/*.json` (see also
`ports/csharp/Contracts.cs` for the C# twin).

- `src/types.ts` — hand-written types (snake_case field names, JSON-shaped)
- `src/schemas.ts` — zod v3 schemas + compile-time checks that `z.infer` matches `types.ts`
- `src/TicketDecision.tsx` — React component rendering a `HandoffEnvelope`
- `test/roundtrip.test.ts` — parse/re-serialize/deep-compare every fixture
- `test/react-render.test.ts` — server-render `TicketDecision` with `react-dom/server`

## Commands

```sh
npm install
npm run build   # tsc -> dist/
npm test        # build + node --test dist/test/
```

Strict schemas (`additionalProperties: false`) use zod `.strict()`;
`AuditEvent` is open (`.passthrough()`), matching the JSON Schema.
