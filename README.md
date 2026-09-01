# Pathless Community Stack

The public, data-safe version of the setup behind the [Pathless Path Community](https://community.pathlesspath.com): a small community platform owned by its members and operator, rather than by a SaaS community host.

This repository is a reference architecture and a working Circle migration toolkit. It shows how I use:

- Cloudflare Pages and Functions for the member-facing portal
- Cloudflare D1 (SQLite) as the community system of record
- Cloudflare R2 for member-owned media
- Resend for magic links and community email
- Stripe for paid access and entitlements
- simple, exportable tables for profiles, spaces, tags, preferences, and access

It deliberately does **not** contain the production UI, private member records, member avatars, course files, email lists, credentials, or historical community posts. Those belong to the community, not to a public code sample.

## What you can use

- [`docs/architecture.md`](docs/architecture.md) explains the setup and the decisions behind it.
- [`docs/migrate-from-circle.md`](docs/migrate-from-circle.md) is the end-to-end Circle exit and cutover playbook.
- [`schema/community.sql`](schema/community.sql) is a portable SQLite/D1 data model.
- [`scripts/import_circle.py`](scripts/import_circle.py) preserves Circle CSV rows and normalizes member data without overwriting member-confirmed profile fields.
- [`scripts/export_d1_sql.py`](scripts/export_d1_sql.py) creates a reviewable SQL import for Cloudflare D1.
- [`examples/circle-export/`](examples/circle-export/) contains synthetic—not real—Circle data for a safe rehearsal.

## Quick start

Requirements: Python 3.10+ and SQLite 3. No Python packages are required.

```bash
python3 scripts/import_circle.py \
  --export-dir examples/circle-export \
  --db private/community.sqlite \
  --community-key example-community \
  --reset
```

Inspect the result:

```bash
python3 scripts/audit_import.py --db private/community.sqlite
sqlite3 private/community.sqlite \
  "select display_name, lifecycle_status from members order by display_name;"
```

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

Prepare a normalized D1 import:

```bash
python3 scripts/export_d1_sql.py \
  --db private/community.sqlite \
  --out private/community-d1-import.sql
```

The `private/` directory is ignored by Git. Keep every real export there (or outside the repository entirely).

## The migration in one picture

```text
Circle CSV export              Member confirmation
       |                              |
       v                              v
raw Circle tables  ----->  normalized community tables  ----->  portal features
(immutable evidence)          (system of record)                  directory
                                                                  field notes
Stripe / manual access  -----> entitlements                       meetups
Resend preferences     -----> email preferences                   matching
```

The important boundary is between imported facts and member-owned answers. A reimport may refresh a Circle avatar URL or activity count. It must not silently replace a location, bio, privacy choice, or matching preference that a member has already confirmed.

## Before using this in production

This is an opinionated starting point, not a hosted product. Add authentication, authorization, rate limiting, backups, deletion workflows, monitoring, and jurisdiction-appropriate privacy terms for your situation. Treat Circle exports as sensitive personal data.

Start with the [migration playbook](docs/migrate-from-circle.md), rehearse on the synthetic files, and keep Circle available in read-only or fallback mode until the reconciliation checks pass.

## License

Code and original documentation are available under the [MIT License](LICENSE). The Pathless Path name and branding are not granted by that license.
