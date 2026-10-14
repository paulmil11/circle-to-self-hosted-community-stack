# Circle to Self-Hosted Community Stack

The public, data-safe reference behind the [Pathless Path Community](https://community.pathlesspath.com): a small, independently operated platform for helping people find one another.

Move from Circle to your own community platform with a Python migration toolkit, a portable SQLite/Cloudflare D1 schema, and guides for member directories, courses, and weekly community emails. Here, “self-hosted” means you control the application and data in your own provider accounts; the reference setup uses managed Cloudflare services, not a turnkey server you install.

## A note from Paul

If you are finding this and looking for the final encouragement to build your own platform, here you go. You can do it. I believe in you. I am giving you permission.

I think building your own platforms is very important to being able to serve people digitally. Standardized online platforms flatten our experiences. Creating your own weird portal can help you stay energized about the people you want to connect with, and help you do interesting things in a cheap or simple way.

I always wanted a community where the most important thing was connecting the nodes inside it. Something in the spirit of “finding the others,” rather than a top-down thing for me to sell and monetize. The weekly member signal email is a big part of that: it helps people notice who has moved somewhere new, shared something interesting in the chat, offered a conversation, or decided to host an event.

With the new platform, more of this is happening with much less of my hands-on support. That feels like the best way to run a community. Most of the value is accruing beyond the platform itself.

## Want to build your own?

Here's my suggested approach:

1. **Ask for your data.** Email Circle, or whatever platform you're using, and ask for an export of your community's data.
2. **Build something that feels like yours.** Give Codex or Claude Code access to the export in a private workspace. Ask it to help you spin up a cool community, and have it ask you questions about what you actually want: how people should connect, which features matter, and the designs or templates you like.
3. **See if it excites you.** If it does, keep going. Build it, try it, and make sure people can use it. Then think about cancelling the old platform.

You can start with a prompt like this:

```text
I want to build my own community platform using this export. Ask me questions
one at a time about the community I want to create, how I want people to
connect, the features I care about, and designs or templates I like.

Then help me build a small local prototype I can try. Keep the real member
data private and use fictional people in demos and screenshots. Help me
figure out what needs to work before I invite members or cancel my old platform.
```

The [migration playbook](docs/migrate-from-circle.md) gives you the practical checks when you're ready. You don't have to decide to leave before you've made something you want to keep building.

## What is here

This repository is a reference architecture and a working Circle migration toolkit. It shows how I use:

- Cloudflare Pages and Functions for the member-facing portal
- Cloudflare D1 (SQLite) as the community system of record
- Cloudflare R2 for member-owned media
- Resend for magic links and community email
- Stripe for paid access and entitlements
- simple, exportable tables for profiles, spaces, tags, preferences, and access

This is a working migration toolkit plus implementation guides, not a deployable copy of the community app. It includes sanitized screenshots of the real interface with fictional member data and course answers. Production UI source, private member records, avatars, course media, email lists, credentials, and historical community posts remain private.

![Community directory with fictional members](docs/screenshots/community-directory.png)

[See the community and course screenshots](docs/screenshots.md).

## What it costs me

As reported by Paul in October 2026, Cloudflare costs about **$5.38 per month** and Resend costs about **$20 per month**: approximately **$25.38 per month combined**.

These are my running costs for those two services, not a vendor quote or an all-inclusive budget for someone else's platform. Payment processing, domains, video hosting, other services, and your time are separate where applicable. Usage and pricing can change.

## What you can use

- [`docs/architecture.md`](docs/architecture.md) explains the setup and the decisions behind it.
- [`docs/best-practices.md`](docs/best-practices.md) covers current deployment, authentication, privacy, billing, email, and recovery practices.
- [`docs/course-portal.md`](docs/course-portal.md) walks through adding courses, protected media, progress, and a private learner notebook.
- [`docs/weekly-member-signals.md`](docs/weekly-member-signals.md) explains the weekly email, Paul's editorial role, and the philosophy of connecting members.
- [`docs/screenshots.md`](docs/screenshots.md) shows the interface and explains how the captures were sanitized.
- [`docs/migrate-from-circle.md`](docs/migrate-from-circle.md) is the end-to-end Circle exit and cutover playbook.
- [`schema/community.sql`](schema/community.sql) is a portable SQLite/D1 data model.
- [`scripts/import_circle.py`](scripts/import_circle.py) preserves Circle CSV rows and normalizes member data without overwriting member-confirmed profile fields.
- [`scripts/export_d1_sql.py`](scripts/export_d1_sql.py) creates a reviewable SQL import for Cloudflare D1.
- [`examples/circle-export/`](examples/circle-export/) contains synthetic—not real—Circle data for a safe rehearsal.
- [`schema/courses.sql`](schema/courses.sql) and [`examples/course-portal/seed.sql`](examples/course-portal/seed.sql) provide an optional course data model and fictional curriculum.

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

Start with the [migration playbook](docs/migrate-from-circle.md), rehearse on the synthetic files, and keep Circle available in read-only or fallback mode until the reconciliation checks pass. Work through the [production practices](docs/best-practices.md) before accepting real members or payments. Screenshots illustrate the interface; they do not certify that every recommended backend control is implemented in the original app.

## License

Code and original documentation are available under the [MIT License](LICENSE). The Pathless Path name and branding are not granted by that license.
