# Building and operating a small community platform

Reviewed against the linked provider documentation on 14 October 2026. These are implementation recommendations for a new platform; the public repository supplies a migration toolkit, not authentication, billing, or a hosted application.

## Keep the system understandable

Start with sign-in, a member-controlled profile, a directory, and one useful way to connect. Add events, books, courses, or matching when members have a reason to use them. Keep identity, access, email preferences, and content in separate tables. An email provider is not your member database, and a payment receipt is not a profile.

Paul reports roughly $5.38/month for Cloudflare and $20/month for Resend in October 2026. Treat those as one small platform's actual costs. Set usage alerts for your own account and budget separately for video, payments, domains, and maintenance where relevant.

## Choose hosting deliberately

The existing portal uses Pages and Pages Functions. For a new Cloudflare build, evaluate Workers with Static Assets: one deployment can serve the interface and APIs, with access to scheduling and other Workers features. Keep an existing Pages app if it meets your needs; a migration is a separate project with route, binding, and custom-domain checks. [Cloudflare's Pages-to-Workers guide](https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/) describes the differences.

A static asset can be served before your Worker runs. Keep paid lesson bodies and private files outside the public asset bundle. If a resource must pass through authentication, configure the appropriate `assets.run_worker_first` routes and test direct URLs as a signed-out user. A client-side redirect does not protect a bundled lesson. See [Worker routing](https://developers.cloudflare.com/workers/static-assets/routing/worker-script/).

Keep development, preview, and production databases, buckets, secrets, and email settings separate. Previews should use synthetic records and a test recipient allowlist. Pin your tool dependencies in a lockfile, commit the deployment configuration, set a deliberate compatibility date, and test dependency or runtime upgrades before deploying. Deploying the interface must not silently run a production migration or send email.

## Make access checks boring and consistent

Use a maintained authentication implementation when possible. For email links, return the same public response whether an address is eligible or unknown. Generate random tokens, store hashes, enforce short expiry, and consume a token atomically so two requests cannot both redeem it. Rate-limit requests independently by account and network source. Build links from an approved origin and allowlist local return paths. Keep tokens out of logs, analytics, and referrers. Email security scanners may follow links: consider a confirmation step before redemption. These recommendations adapt the token handling principles in [OWASP's recovery guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).

Use secure, HTTP-only session cookies with an appropriate SameSite policy, explicit expiry, and server-side revocation. Rotate sessions after login and sensitive account changes; clear them on logout. Check Origin and use CSRF protection on cookie-authenticated writes. Never make destructive changes through GET requests. See [OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

Authorize every read and write on the server. Derive the member ID from the session, check active entitlements including start/end dates, and scope private records to that member. Validate IDs and ownership even when the UI hides the action. Require explicit admin rights and stronger authentication for administrator access. Test both a signed-out visitor and a signed-in member trying to read somebody else's notes. See [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

## Protect data throughout its lifetime

- Use bound SQL parameters, bounded request bodies, pagination, and indexes for the queries you actually run.
- Render user text safely. Treat Markdown, links, embeds, uploads, and fetched link previews as untrusted input; sanitize allowed markup and validate URL schemes. Do not let a link preview fetch arbitrary internal addresses.
- Return private API responses with `Cache-Control: private, no-store`; avoid shared caching of profiles with hidden fields, messages, notebooks, or signed media URLs.
- Keep precise locations, contact details, unpublished writing, and private reading choices out of directories and digest inputs. Visibility must be an explicit member choice.
- Keep secrets in deployment secrets, not client bundles or committed environment files. Limit deployment credentials to the resources they need.
- Provide account correction, export, and deletion. Include object storage and derived search/analytics data in the deletion plan. Document backup retention and prevent a restore from silently reactivating deleted accounts or unsubscribed recipients.

The importer's email-derived UUIDs are deterministic migration identifiers, not anonymization or access tokens. A known community key and guessed email can reproduce an ID. Keep the key stable for reimports; use a durable identity mapping when members change email, and random IDs for new identities if appropriate. Do not recalculate all member IDs after launch.

## Rehearse database changes and recovery

Use numbered SQL migrations and apply them locally before a separate staging database. Prefer additive changes that old and new app versions can both read. Deploy a compatible app, backfill in bounded steps, and remove obsolete fields in a later release. See [D1 migrations](https://developers.cloudflare.com/d1/reference/migrations/).

Before a production migration, save a private export and a recovery point. Test a restore into a disposable database and verify row counts, foreign keys, access, and a member's ability to sign in. D1 Time Travel provides point-in-time recovery with plan-dependent retention; it complements portable exports. A code rollback does not reverse schema or data changes. See [Time Travel and backups](https://developers.cloudflare.com/d1/reference/time-travel/).

The repository's D1 export omits explicit `BEGIN TRANSACTION` / `COMMIT` wrappers because D1's import format does not accept them. It inserts parent tables before dependent rows, excludes raw source data by default, and is intended for a fresh database. `INSERT OR IGNORE` is not a synchronization strategy: reconcile counts and conflicts after import. See [D1 import/export guidance](https://developers.cloudflare.com/d1/best-practices/import-export-data/).

## Make billing retryable

Grant paid access from verified payment events, not the browser's checkout-success page. Verify the webhook signature against the raw request body. Store provider event IDs with a uniqueness constraint and commit the access change with the event's processing status atomically, or durably queue work before acknowledging receipt. A failed attempt must remain retryable.

Expect duplicates and events arriving out of order. Reconcile current provider state and serialize conflicting changes rather than allowing an old event to restore revoked access. Handle delayed payment success/failure, refunds, cancellations, and disputes according to an explicit access policy. Revoke only the affected grant: a cancelled subscription should not erase an independent lifetime purchase or gift. See [Stripe webhook guidance](https://docs.stripe.com/webhooks).

## Keep email useful and optional

Keep sign-in and essential account mail separate from digests and announcements. A segment says which group a person belongs to; a topic says what they want to receive. Preserve global unsubscribe and suppression state, and select the appropriate topic for each community broadcast. Do not automatically resubscribe someone because they signed in or bought access. See [Resend topics](https://resend.com/docs/dashboard/contacts/manage-topics).

For the weekly email, gather evidence, write a useful letter, preview it, and approve the exact content before sending. Store a send journal so a timeout cannot trigger a duplicate broadcast. A partial send needs reconciliation with the provider. The [member signal guide](weekly-member-signals.md) explains the full workflow.

## Check the outcomes that matter

Before launch, exercise expired and reused login links, revoked access, cross-member reads/writes, duplicate payment events, failed email delivery, hidden locations, and a real restore. Test keyboard navigation, visible focus, readable form labels, narrow screens, and reduced motion. Courses also need captions or transcripts and an accessible alternative to interactive exercises.

Use structured logs with request IDs and event types, excluding tokens, private message bodies, notebook answers, and unnecessary personal data. Alert on failed sign-ins, webhook backlogs, database errors, and delivery failures. Recheck the deployed custom domain and asset version after a release.

The product test is simpler: did someone find a useful person, conversation, or opportunity? More page views are not automatically a healthier community.
