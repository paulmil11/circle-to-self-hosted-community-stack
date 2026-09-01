# Security and privacy

Please report security issues privately to the repository owner rather than opening a public issue with exploit details.

## Data handling

Circle exports contain names, email addresses, profile fields, activity, and sometimes private community content. Keep real exports, generated SQLite databases, SQL dumps, reports, and downloaded media outside Git. This repository ignores the conventional `private/`, `data/`, and `exports/` paths, but an ignore rule is not a security boundary.

Before any public push:

1. Inspect `git status --ignored`.
2. Search the complete staged diff for emails, tokens, private URLs, and member names.
3. Run a secret scanner if one is available.
4. If personal data or a secret was ever committed, remove it from history and rotate affected credentials. A later deletion commit is not sufficient.

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
