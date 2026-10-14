# The weekly member signal email

## Why I make it

I always wanted a community where the most important thing was connecting the nodes inside it. I wasn't trying to build a top-down thing for me to sell and monetize. I wanted to help people find the others.

The weekly email is one way I do that. Someone has moved to a new city. Someone has shared a link in the chat, made something, offered a conversation, or decided to host an event. These are small signals, but they can become a friendship, a collaboration, or the nudge someone needed.

With the new platform, I can gather what's happening across the community each week and turn it into a useful letter. More things are happening, and they take much less of my hands-on support to happen. That feels like the best way to run a platform or community: most of the value is accruing beyond the platform itself.

— Paul

## What the system notices

The email draws from first-party community activity and specifically approved group chat sources. “Scan the community” means those permitted sources, not every private message, notebook, or connected chat account.

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

An import is not new participation. A private reading list is not a public recommendation. A timestamp changed by a bulk migration is not evidence that everyone just moved or joined. The collector records uncertainty so these cases can be left out or checked.

## What I craft each week

The system gathers candidates; I shape the letter. I add a personal introduction, decide what deserves attention, connect related contributions, and remove repetition. It should sound like a useful note from a person who knows the group.

Each item should make the next action obvious: visit a profile, reply to a member, join a conversation, RSVP, read the post, or explore what someone made. Link back to the member or source. Don't turn someone's casual comment into a promotional testimonial, invent a chat invite link, or imply an endorsement they did not give.

The aim is a shared community letter with relevant variations, not a different AI-generated narrative for every member. Where a verified in-person event is relevant, a regional edition can have a local subject and a short invitation after the shared introduction. Match only explicitly shared locations, send each person one edition, and expire the invitation when the event begins. Unknown or hidden locations receive the standard edition. Virtual events stay in the shared letter.

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

1. **Collect one exact window.** Start after the previous successfully sent issue's collection cutoff and end at the current collection time. A first run can use seven days. A skipped week means the next issue covers the unsent span. Tests and failed or partial sends do not advance the cutoff.
2. **Keep evidence with each candidate.** Store signal type, member ID, source, source timestamp, destination URL, short description, confidence, and include/skip decision in private working notes. Use the same window for the approved chat sources. Do not copy private room identifiers or raw chat exports into this public repository.
3. **Require fresh data.** If the live collection fails, stop with an explanation. Do not silently write a fresh-sounding letter from an old local database. Merge queued notes and unsent drafts; compare with prior sent items so repeats need a meaningful update.
4. **Curate and preview.** Check people, links, dates, time zones, and event expiry. Keep evidence and editorial explanations in separate notes for Paul. Preview the actual email and every proposed regional subject/body.
5. **Approve the exact draft.** The existing implementation hashes the reviewed draft, including the variants and any send window. Editing it invalidates that approval. A preview or test send does not authorize a production broadcast.
6. **Resolve recipients at send time.** Intersect eligible members with subscribed contacts in the community segment. Use the Weekly Digest topic and preserve provider suppression/unsubscribe preferences. Do not create subscriptions while preparing an issue.
7. **Record the send.** Save provider broadcast IDs, edition assignment, attempt state, and completion. Inspect both journal and provider status before retrying after a failure. Do not resend the whole issue because one step timed out.
8. **Learn without overclaiming.** Review delivery, distinct clicks, bounces, complaints, and unsubscribes. Missing metrics stay unknown. Email scanners affect opens and clicks; neither proves a friendship, RSVP, or book recommendation happened.

The production workflow can add recipient-specific sign-in links at send time to reduce friction. Those links are credentials: exclude them from public examples, screenshots, analytics, and ordinary link reports; disable third-party click tracking for credential-bearing links. Keep redemption short-lived and one-time, account for email scanners, and provide a normal sign-in fallback. A regular destination link is a simpler starting point for a new platform.

## A small fictional example

> Hi all,
>
> A few things you might want to follow up on this week:
>
> - Avery has shared a new location in Lisbon and would love to meet other people experimenting with independent work.
> - Robin is hosting a reading hour. Bring whatever you're reading; the event page has the time and RSVP details.
> - Jules posted a small writing project in the group. Take a look and send them a note if it resonates.
> - Morgan is offering a curiosity conversation about making room for creative work.
>
> If one of these gives you a reason to reach out, do it. You don't need to wait for me to make an introduction.

These names and activities are invented to illustrate the format. A real edition includes verified profile, event, and source links, a personal opening, and the required preference/unsubscribe information.

## Build the smallest useful version

Start with one weekly read-only query, a private candidate file, and a manually reviewed email. Add chat sources only after deciding which rooms are appropriate for digest reuse. Add regional editions when they help people attend real events. Automate collection, duplicate checks, and delivery bookkeeping before trying to automate editorial judgment.

The public repository documents this operating pattern; it does not ship the production collector, chat integration, or sender. Apply the [email and access practices](best-practices.md) when implementing it. For provider-specific subscription behavior, see [Resend's topic documentation](https://resend.com/docs/dashboard/contacts/manage-topics).
