# Migrating from Circle

This is the playbook used to turn Circle from the community system of record into a seed export for an operator-owned portal. It is designed for a staged exit: inventory, export, rehearse, confirm, cut over, and only then close the old platform.

Do not cancel Circle first. A migration is complete when members can sign in, access is reconciled, durable media is owned by you, email consent is preserved, and rollback has stopped being necessary.

## 1. Decide what is moving

Create an inventory before touching data.

| Circle object | Destination | Migration rule |
| --- | --- | --- |
| Members and profile fields | `members`, `member_profiles` | Import as prefill; ask members to confirm public fields |
| Tags | `member_tags` | Preserve as source signals, not permanent truth |
| Space membership | `member_space_access` | Preserve for audit and initial access mapping |
| Posts and comments | raw archive or selected new content tables | Do not auto-publish private history without deciding the member expectation |
| Events and attendees | events archive/new events tool | Preserve times in UTC and verify time zones |
| Avatars and uploads | your object storage | Download before Circle URLs or permissions change |
| Live recordings/transcripts/chat | your archive | Export each artifact explicitly; they are not equivalent data types |
| DMs and chat spaces | usually archive-only or intentionally left behind | Confirm availability and member expectations before promising portability |
| Paywalls/subscriptions | Stripe plus `entitlements` | Reconcile independently; never infer active billing from a profile tag alone |
| Marketing consent | email provider plus `member_email_preferences` | Preserve unsubscribes and suppressions before sending anything |

Write down what will not move. Old conversational exhaust may be better as a private archive than as a permanent feature in the new home.

## 2. Export Circle data

Circle's interface and plan features change. Checked against Circle's official documentation on 14 October 2026, the member export flow is:

1. Click **Audience** in the left sidebar, then select **Audience** to open Manage audience.
2. Open **All** if you want the complete audience, including non-member contacts, and clear filters.
3. Select **More → Export CSV**.
4. Retrieve the generated export from the admin account's email.

Circle documents the member fields currently included in this export—identity, profile, tags, activity, marketing preference, invitation state, and related fields—in [Export a CSV of your members](https://help.circle.so/p/administration/analytics/export-a-csv-of-your-members).

Also collect, where relevant:

- space or space-group member CSVs from each space's member settings;
- event attendee CSVs;
- analytics downloads needed for historical comparisons;
- live participant lists and [live chat logs](https://help.circle.so/p/live-and-events/live-management/download-a-live-chat-log);
- [live recordings and transcripts](https://help.circle.so/c/live-management/view-and-manage-live-recordings);
- Stripe customer, subscription, invoice, and transaction exports;
- the suppression/unsubscribe state from your email provider;
- originals of images, files, embeds, and downloads that matter.

If your Circle account offers a full community export containing members, spaces, posts, comments, and events, request it and retain the generated `README.txt` with the CSVs. Export availability and filenames vary; this toolkit discovers CSVs by object name and also accepts explicit file paths.

Circle's [Data API documentation](https://api.circle.so/apis/data-api) notes that CSV exports are manual and do not cover every API use case. For a large or frequently changing community, use the API available to your plan or arrange an export with Circle support rather than scraping pages.

### Exit-safety notes

- Deactivation and deletion are different. Circle says deactivation retains a member's content, while deletion permanently erases profile and content. Review [Circle's removal behavior](https://help.circle.so/p/audience/member-management/removing-members-from-your-community) before cleaning up accounts.
- Do not assume an analytics download is a content backup. It may contain aggregates or leaderboard rows rather than post bodies.
- Do not assume avatar and attachment URLs remain usable after cancellation.
- Do not migrate globally unsubscribed contacts into a subscribed marketing segment.
- Store the untouched export read-only and record its timestamp and checksum.

Suggested private layout:

```text
private/
  circle-export-YYYY-MM-DD/
    README.txt
    your_community_members.csv
    your_community_spaces.csv
    your_community_posts.csv
    your_community_comments.csv
    your_community_events.csv
  billing/
  email/
  media/
```

The repository ignores `private/`; keeping the data outside the repository is even safer.

## 3. Rehearse locally

First run the synthetic rehearsal:

```bash
python3 scripts/import_circle.py \
  --export-dir examples/circle-export \
  --db private/rehearsal.sqlite \
  --community-key example-community \
  --reset

python3 scripts/audit_import.py --db private/rehearsal.sqlite
```

Then use a real export in a new rehearsal database. `--community-key` must be stable for every run because it namespaces deterministic member IDs. Use a non-secret slug or domain; changing it produces different IDs. These IDs are not anonymization or authorization credentials. After launch, account email changes need a durable source-identity mapping so a reimport cannot create a second identity.

```bash
python3 scripts/import_circle.py \
  --export-dir private/circle-export-YYYY-MM-DD \
  --db private/community.sqlite \
  --community-key your-community-domain \
  --report private/import-report.json \
  --reset
```

`--reset` deletes the destination database. Use it only for a disposable rehearsal or a deliberate rebuild before members have started editing their profiles. Omit it for a reimport into an existing database; the profile-preservation behavior applies to non-reset imports.

The importer:

- reads UTF-8 CSVs and tolerates a UTF-8 BOM;
- preserves duplicate header names as `Header`, `Header__2`, and so on;
- stores every raw row before normalizing it;
- uses normalized email as the initial identity key;
- creates stable opaque member IDs;
- parses known space names longest-first so names containing commas survive;
- treats tags as migration signals;
- writes counts and non-PII warnings to the report;
- leaves member-confirmed profile records in their own table.

Use explicit paths if auto-discovery is ambiguous:

```bash
python3 scripts/import_circle.py \
  --export-dir private/circle-export-YYYY-MM-DD \
  --members private/circle-export-YYYY-MM-DD/audience.csv \
  --spaces private/circle-export-YYYY-MM-DD/spaces.csv \
  --db private/community.sqlite \
  --community-key your-community-domain \
  --reset
```

## 4. Reconcile before launch

Run the audit and save the output with the private migration record:

```bash
python3 scripts/audit_import.py \
  --db private/community.sqlite \
  --json private/audit.json
```

Check at least:

- raw member rows versus normalized members;
- rows skipped for missing email;
- duplicate normalized emails;
- active, cancelled, gifted, lifetime, and unknown lifecycle counts;
- tag and space-access counts;
- members with remote Circle avatar URLs still present;
- member emails against Stripe customers/subscriptions;
- member emails against Resend contacts and suppression state;
- a sample from every custom profile field;
- Unicode, embedded newlines, commas in space names, and empty values;
- event times across at least two time zones;
- a random sample of post/comment parent relationships.

Useful queries:

```sql
select lifecycle_status, count(*)
from members
group by lifecycle_status
order by lifecycle_status;

select count(*) as still_circle_hosted
from members
where avatar_url like 'http%circle%';

select s.name, count(*) as members
from member_space_access msa
join circle_spaces s on s.circle_space_id = msa.circle_space_id
group by s.name
order by members desc;
```

Reconcile billing separately. The safest rule is: Circle tags may create provisional access, but active Stripe subscriptions, completed lifetime payments, documented gifts, and reviewed manual grants decide launch access.

## 5. Ask members to confirm

Do not silently turn imported profile data into a public directory. On first sign-in, ask members to confirm:

- preferred name and headline;
- city/region display and location visibility;
- bio, website, and contact links;
- interests, skills, and what they want help with;
- matching preferences;
- email preferences;
- acceptance of the new privacy terms.

Keep the flow short and prefilled. Store confirmed answers in `member_profiles`, set `confirmed_at`, and show a clear way to edit or hide the profile later.

## 6. Load the destination

For Cloudflare D1, create a new empty database, apply the schema, generate a reviewable normalized-data import, and then execute it. These commands follow Cloudflare's current [D1 import guidance](https://developers.cloudflare.com/d1/best-practices/import-export-data/).

```bash
npx wrangler d1 create your-community
npx wrangler d1 execute your-community --remote --file schema/community.sql

python3 scripts/export_d1_sql.py \
  --db private/community.sqlite \
  --out private/community-d1-import.sql

npx wrangler d1 execute your-community \
  --remote \
  --file private/community-d1-import.sql

npx wrangler d1 execute your-community \
  --remote \
  --command "select lifecycle_status, count(*) from members group by lifecycle_status;"
```

The export excludes raw Circle tables and optional course tables by default and uses `INSERT OR IGNORE`, making an accidental repeat safer. It is intended for an empty destination after the schema is applied; ignored conflicts are not updates, so reconcile counts afterward. It omits explicit transaction wrappers for D1 compatibility and orders rows by dependency. Add `--include-raw` only after making a deliberate privacy and retention decision; use `--replace` only if you have reviewed the foreign-key cascade consequences. See the [course guide](course-portal.md) for `--include-courses`, which can include private learner answers.

If the destination already contains data, export a private backup first with `npx wrangler d1 export your-community --remote --output private/pre-migration-backup.sql`. For a Pages portal, bind the resulting D1 database to the Pages Function in Wrangler or the dashboard; Cloudflare documents the current setup in [Pages bindings](https://developers.cloudflare.com/pages/functions/bindings/#d1-databases).

Upload member-owned media to object storage and replace source URLs only after verifying the uploaded object. Keep the download report, but do not commit it—it contains member identifiers.

## 7. Cut over in stages

A low-drama sequence:

1. **Private rehearsal:** operator and one technical reviewer.
2. **Seed group:** a few members representing different access types and profile shapes.
3. **Soft launch:** all eligible members can sign in; Circle remains available as a fallback.
4. **Content freeze:** announce the final Circle write cutoff and run one last delta/full export.
5. **Final reconciliation:** rerun member, billing, email, media, and count checks.
6. **Primary-home switch:** update links, onboarding, email, and event calls to action.
7. **Read-only/archive window:** keep Circle available long enough to handle missing data.
8. **Cancellation:** only after exports, backups, redirects, and support communication are complete.

Tell members what is happening in ordinary language: why the home is changing, what moved, what did not, how privacy works, how to sign in, and where to ask for help.

## 8. Rollback and completion criteria

Before cutover, define a rollback decision and an owner. A DNS change can be reverted; lost member content or cancelled billing cannot.

Migration is complete when:

- every eligible member has a deterministic record and intended access;
- subscription and lifetime access counts reconcile;
- unsubscribes and suppressions are preserved;
- members can authenticate without Circle;
- critical media no longer depends on Circle URLs;
- member-confirmed fields survive a reimport test;
- data export, correction, and deletion workflows exist;
- backups restore successfully;
- support and rollback windows have closed;
- Circle has been cancelled only after the preceding checks pass.

## Field mapping reference

Circle changes column labels over time, so the importer accepts common aliases.

| Circle field | Destination |
| --- | --- |
| `UID` or `User ID` | `members.circle_user_id`, raw source record |
| `First Name`, `Last Name` | member identity and profile prefill |
| `Email` | canonical initial identity key |
| `Join Date` | `members.circle_joined_at` |
| `Active (Signed In Last 30 Days)` | `members.circle_active_30d` |
| `Tags` | `member_tags`, provisional lifecycle/access signals |
| `Headline` | `members.headline` prefill |
| `Bio` | `members.bio` prefill |
| `Location` | `members.location_text` prefill; never automatic visibility |
| `Website` and social URLs | `members.social_links_json` |
| `Avatar URL` | temporary source URL until copied to owned storage |
| `Last Active` | `members.circle_last_active_at` |
| `Space Access` | `member_space_access` |
| activity/gamification fields | `members.circle_activity_json` |

Keep mapping decisions in version control. Keep the actual exported rows private.
