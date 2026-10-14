# Community and course screenshots

These captures show the Pathless Path interface rendered locally with fictional members, locations, recommendations, and learner answers. No production account or member database was used. The course examples show the Reinvent interface; the [course guide](course-portal.md) explains how to build the supporting access and storage layers.

## Member directory

Help people find one another by place, interests, and what they are exploring. Members can follow a profile, send a message, or book a conversation.

![Member directory with six fictional profiles](screenshots/community-directory.png)

## Curiosity conversations

Members choose to share a scheduling link and topics they would enjoy talking about. A random suggestion gives someone an easy place to start.

![Curiosity conversation offers from fictional members](screenshots/community-conversations.png)

## Books worth reading

A shared bookshelf gives people another reason to connect. The titles and authors are real; the recommendations and counts in this capture are invented. Book covers use the interface's text placeholders.

![Community book rankings with fictional recommendations](screenshots/community-books.png)

## Course reflection

Lesson navigation, a reflection prompt, and the learner's notebook sit together. The sample answer belongs to a fictional learner; no course video or private media was loaded.

![Reinvent course reflection beside a fictional learner notebook](screenshots/course-reflection.png)

## Course exercise

A small exercise turns an idea into something the learner can try. This capture focuses on the saved exercise panel.

![Action challenge exercise with fictional answers](screenshots/course-exercise.png)

## Notebook review

Bring saved answers and exercises together so a learner can return to them or print their work. This image shows the review header and saved-work area.

![Course notebook review with fictional saved work](screenshots/course-notebook.png)

## Capture notes

Captured on 14 October 2026 from a local checkout of the community interface, using an isolated Chromium context at 1440px desktop width. The exercise is a panel capture; the notebook is cropped to its saved-work area.

- Every API response was replaced with a small fictional fixture before rendering. Names, profile text, locations, scheduling URLs, recommendation counts, and notebook answers were created for these captures.
- Browser storage started fresh and was seeded only with fictional course answers. No real session cookies, sign-in links, or production database were used.
- All external requests were blocked, including fonts, map tiles, and media players. Real member images and course downloads were not served. The map was omitted because no location dataset or tiles were loaded.
- The course playback map and separate lesson-source script were replaced with empty objects. Screenshots retain the interface's visible titles, prompts, and built-in exercise copy; they do not distribute course video, audio, worksheets, or transcripts.
- Presentation-only styles kept type upright and removed decorative labels. Functional navigation, lesson progress, form labels, and save controls remain. No watermark, source footer, or screenshot counter was added.
- All six captures were checked for exposed personal information, clipped main content, and horizontal overflow. They rendered without JavaScript page errors.

To make screenshots of your own platform, use the same pattern: a fresh browser, synthetic responses, blocked external traffic, a narrow static-asset allowlist, and visual inspection before publishing. Blurring a live member screen is an avoidable risk when you can render fictional data from the start.

These images illustrate the interface. They are not a claim that the public repository ships a complete application or that the original app implements every control in the production guides.
