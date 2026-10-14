# Architecture

## Product posture

The Pathless Path portal is meant to feel like a member home, not an enterprise community suite. The technology follows that constraint: a static-first web app, small server functions, and a relational database that can be exported with ordinary tools.

Circle was treated as seed data. The operator-owned database is now the durable member layer for profiles, onboarding, matching, events, email preferences, billing access, books, and courses.

## Stack

| Concern | Choice | Why |
| --- | --- | --- |
| Web UI | Cloudflare Pages | Static-first, simple custom-domain deployment |
| API/auth | Cloudflare Pages Functions | Small request handlers close to the data |
| Relational data | Cloudflare D1 / SQLite | Portable SQL, enough scale for a small community, easy local rehearsals |
| Member media | Cloudflare R2 | Removes durable media dependencies on Circle URLs |
| Authentication email | Resend | Email-first magic links without requiring social login |
| Community email | Resend Contacts/Segments | Explicit preferences and a clean separation from login mail |
| Billing | Stripe | Billing stays an entitlement source, not the member profile database |
| Informal chat | WhatsApp | Used as a complementary high-frequency channel, not the system of record |

These providers are replaceable. The durable design is the division of responsibilities and the portable data model, not a particular vendor.

The table describes the existing portal. For a new build, also evaluate Workers with Static Assets; see the [current production practices](best-practices.md) for deployment, route protection, backups, and email operations. Paul's reported October 2026 costs are about $5.38/month for Cloudflare and $20/month for Resend, approximately $25.38 combined for those services.

## Data flow

```text
                         +--------------------+
Circle exports -------->| raw Circle tables  |
                         +---------+----------+
                                   |
Stripe events ----------+          | normalize/reconcile
                        |          v
Manual grants ----------+--> members + entitlements <---- member onboarding
                        |          |
Resend preferences -----+          +--> directory, posts, meetups, matching
                                   |
                                   +--> member export/deletion workflows
```

### Raw source layer

Every source row is stored as JSON together with an import batch and row number. This makes header changes, duplicated headers, and normalization mistakes recoverable. Raw tables are evidence, not application tables.

### Normalized layer

`members` holds canonical identity and source-prefill fields. Tags, space access, email preferences, and entitlements live in separate tables because they change independently and have different privacy rules.

### Member-confirmed layer

`member_profiles` holds member-owned answers and privacy settings. Once `confirmed_at` is set, reimports do not overwrite those values. This is the most important rule in the migration toolkit.

## Identity and access

Email is the initial identity key because it exists in Circle and Stripe exports. The importer derives deterministic UUIDv5 member IDs from a stable community key and normalized email. This makes rehearsals repeatable, but it is not anonymization: someone who knows the community key can reproduce an ID from a guessed email. Never treat a member ID as proof of authorization. Preserve the canonical ID when an account changes email; reconcile future imports through a durable source-identity mapping instead of recreating the member.

Production authentication uses one-time email links:

1. Accept an email only for an eligible member.
2. Generate a cryptographically random token.
3. Store only its hash with a short expiry.
4. Send the usable token by email.
5. Consume it once and create a secure, HTTP-only session cookie.
6. Hash the session token in the database as well.

Login messages are transactional. Digests, event notes, nearby-member messages, and matching introductions are optional community email governed by `member_email_preferences`.

## Entitlements

Access is modeled separately from identity. A member may have community access because of an active Stripe subscription, a lifetime purchase, a gift, a course purchase, or a manual decision. Each source writes an entitlement with its own status and dates.

This prevents a legacy Circle tag from remaining the permanent billing truth. During migration, tags can create provisional entitlements; after cutover, Stripe webhooks and audited manual changes become authoritative.

## Location privacy

Imported Circle locations are prefill suggestions. A member appears in a directory or map only after confirmation and explicit visibility consent. Store city/region-level coordinates for discovery; do not turn a profile location into a precise address.

## Operational pattern

The operating loop is intentionally small:

- member activity is stored in first-party tables;
- a weekly digest script collects candidate signals;
- a human reviews and approves the digest;
- sending respects member preferences and suppression state;
- delivery failures update the preference record and alert the operator;
- admin changes write an audit note rather than silently changing access.

The system optimizes for legibility. At small-community scale, a reviewable SQL file and a clear runbook are usually better than an elaborate data pipeline.

The [weekly member signal email](weekly-member-signals.md) is an example of this philosophy in practice. It gathers activity that can help members find one another, while Paul shapes the letter. Its purpose is to make conversations, projects, and gatherings easier, including those that happen beyond the platform.

## Courses as an extension

Reuse member identity and explicit course entitlements. Keep curriculum, progress, and private notebook entries separate; authorize lesson and media requests before returning protected content. The [course portal guide](course-portal.md) includes an additive schema, synthetic seed, API design, and launch checks. The screenshots show the existing Reinvent interface; its browser-local notebook is a UI example, not an implementation of the recommended server-backed storage.

## What is not in this public repository

The production interface and operations contain member-authored writing, member images, benefits negotiated with partners, course materials, and community-specific editorial judgment. This repository shares the architecture, schema, migration mechanics, and reviewed screenshots with fictional member data and learner answers. It does not distribute the production UI source, member content, private files, or course media.
