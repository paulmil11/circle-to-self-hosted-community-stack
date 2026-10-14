# Security and privacy

Please report security issues privately to the repository owner rather than opening a public issue with exploit details.

## Data handling

Circle exports contain names, email addresses, profile fields, activity, and sometimes private community content. Keep real exports, generated SQLite databases, SQL dumps, reports, and downloaded media outside Git. This repository ignores the conventional `private/`, `data/`, and `exports/` paths, but an ignore rule is not a security boundary.

Before any public push:

1. Inspect `git status --ignored`.
2. Search the complete staged diff for emails, tokens, private URLs, and member names.
3. Run a secret scanner if one is available.
4. If personal data or a secret was ever committed, remove it from history and rotate affected credentials. A later deletion commit is not sufficient.

Create screenshots with synthetic identities and activity in an isolated browser. Block external requests except the specific public assets needed for the capture. A user-supplied image needs a separate privacy review; the published map shows aggregate locations without member names. Do not publish real avatars, private writing, learner answers, signed media URLs, magic links, room IDs, or admin/billing views. Review the rendered pixels as well as the staged files. See [screenshot capture notes](docs/screenshots.md).

Deterministic import IDs are not anonymization. The community key is not a secret and a guessed email can reproduce a member ID. Server-side authorization is still required for every protected resource.

## Production checklist

- Encrypt data in transit and use the hosting provider's encryption at rest.
- Hash session and magic-link tokens; never store usable tokens.
- Enforce authorization in server-side code, not only in the UI.
- Rate-limit login, search, uploads, and write endpoints.
- Keep admin access explicit and auditable.
- Back up the normalized database and test restores.
- Implement member export, correction, and deletion requests.
- Keep precise location private; publish only member-confirmed display locations.
- Separate transactional authentication email from optional community marketing email.

See [production practices](docs/best-practices.md), [course access and notebook handling](docs/course-portal.md), and [weekly signal sourcing and approval](docs/weekly-member-signals.md) for implementation details. These guides describe controls to build; this migration toolkit does not supply a production authentication or payment system.
