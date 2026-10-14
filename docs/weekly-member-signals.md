# The weekly member signal email

## Help members find the others

I always wanted a community where the most important thing was connecting the nodes inside it. I wasn't trying to build a top-down thing for me to sell and monetize. I wanted to help people find the others.

The weekly email helps. Someone has moved to a new city. Someone has shared a link in the chat, made something, offered a conversation, or decided to host an event. These are small signals, but they can become a friendship, a collaboration, or the nudge someone needed.

With the new platform, I can gather what's happening across the community each week and turn it into a useful letter. More things are happening, and they take much less of my hands-on support to happen. That feels like the best way to run a platform or community: most of the value is accruing beyond the platform itself.

## What the system notices

The email draws from shared community activity and approved group chats. Private messages and learner notebooks stay out of the collection.

| Signal | What a member can do with it |
| --- | --- |
| New or newly activated members | Welcome someone with a shared interest |
| Member-shared location changes | Find someone nearby or reconnect in a new city |
| Travel plans and in-person invitations | Arrange a walk, coffee, or local gathering |
| Upcoming virtual events | Join from wherever they are |
| Asks and offers | Help someone or accept an offer |
| Curiosity conversation offers | Start a conversation around a real shared question |
| Member creations and links in approved chats | Discover what someone is making and follow up |
| Field Notes and replies | Read a thoughtful contribution and continue the discussion |
| Public book recommendations | Find something to read and someone to talk about it with |

Exclude imports, private reading lists, and timestamps changed by bulk migrations. Keep uncertain items for review rather than presenting them as new member activity.

## What I craft each week

The system gathers candidates; I shape the letter. I add a personal introduction, decide what deserves attention, connect related contributions, and remove repetition. It should sound like a useful note from a person who knows the group.

Each item should make the next action obvious: visit a profile, reply to a member, join a conversation, RSVP, read the post, or explore what someone made. Link back to the member or source. Don't turn someone's casual comment into a promotional testimonial, invent a chat invite link, or imply an endorsement they did not give.

Members receive a shared community letter, with regional variations when useful. Where a verified in-person event is relevant, a regional edition can have a local subject and a short invitation after the shared introduction. Match only explicitly shared locations, send each person one edition, and expire the invitation when the event begins. Unknown or hidden locations receive the standard edition. Virtual events stay in the shared letter.

## The operating loop

```text
Last successful issue's collection cutoff
                    |
                    v
Fresh portal signals + approved chat sources + Paul's queued notes
                    |
                    v
Candidates with evidence -> deduplicate -> Paul edits the letter
                    |
                    v
Preview standard/regional editions -> approve exact content
                    |
                    v
Eligible subscribed recipients -> send journal -> delivery report
                    |
                    v
Next issue starts at this issue's collection cutoff
```

1. Collect activity after the last successfully sent issue's cutoff, ending at the current collection time. Start with seven days for the first issue. A skipped week carries forward; tests and failed or partial sends do not advance the cutoff.
2. Keep the source, timestamp, member ID, destination link, and include/skip decision for each candidate in private working notes. Apply the same window to approved chats.
3. Stop if fresh collection fails. Merge queued notes and unsent drafts, and compare with prior issues so repeated items need a meaningful update.
4. Check names, links, dates, time zones, and expired events. Preview the email and every regional subject/body. Keep editorial notes separate from the letter.
5. Approve the exact draft. The existing workflow hashes the reviewed content, variants, and send window. Editing them invalidates approval. A test send does not authorize a broadcast.
6. Resolve recipients at send time: eligible members who are subscribed to the community segment and Weekly Digest topic. Preserve unsubscribes and suppressions; preparing an issue must not create subscriptions.
7. Record provider IDs, edition assignments, attempts, and completion. After a failure, check the journal and provider status before retrying. A timeout must not trigger a second send to everyone.
8. Review delivery, distinct clicks, bounces, complaints, and unsubscribes. Missing metrics stay unknown. Email scanners affect opens and clicks, so neither proves that a conversation or meetup happened.

The production workflow can add recipient-specific sign-in links at send time to reduce friction. Those links are credentials: exclude them from public examples, screenshots, analytics, and ordinary link reports; disable third-party click tracking for credential-bearing links. Keep redemption short-lived and one-time, account for email scanners, and provide a normal sign-in fallback. A regular destination link is a simpler starting point for a new platform.

## What the letter looks like

![Weekly email in the actual template, using fictional activity](screenshots/member-email.png)

The names and activities in this example are invented. A real edition includes verified profile, event, and source links, a personal opening, and preference/unsubscribe controls. [The README diagram](../README.md#from-an-update-to-a-connection) shows how an item in the letter can lead to members connecting directly.

## Build the smallest useful version

Start with one weekly read-only query, a private candidate file, and a manually reviewed email. Add chat sources only after deciding which rooms are appropriate for digest reuse. Add regional editions when they help people attend real events. Automate collection, duplicate checks, and delivery bookkeeping before trying to automate editorial judgment.

The public repository documents this operating pattern; it does not ship the production collector, chat integration, or sender. Apply the [email and access practices](best-practices.md) when implementing it. For provider-specific subscription behavior, see [Resend's topic documentation](https://resend.com/docs/dashboard/contacts/manage-topics).
