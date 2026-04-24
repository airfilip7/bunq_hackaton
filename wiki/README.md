# bunq Nest — wiki

Internal docs for the team. Read these alongside `CLAUDE.md` at the project root, which holds product framing, regulatory guardrails, prompts, and demo plan.

| Doc | What's in it |
|---|---|
| [`architecture.md`](architecture.md) | System overview, components, end-to-end flow, AWS image pipeline, deployment shape, scope boundaries. Start here. |
| [`agent-loop.md`](agent-loop.md) | The chat agent's turn lifecycle. Streaming protocol, tool schemas, the read-vs-write split, the human-in-the-loop approval pattern, failure modes. |
| [`data-model.md`](data-model.md) | DynamoDB single-table design and S3 layout. Item shapes, access patterns, what's deliberately not modeled. |

If you change architectural decisions, update `CLAUDE.md` (one-paragraph summary) and the relevant wiki doc (full detail). The wiki is the source of truth for how the system fits together.
