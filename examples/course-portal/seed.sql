-- Fictional curriculum only. No students, paid media, or usable credentials.
-- Run after schema/community.sql and schema/courses.sql in a rehearsal database.
PRAGMA foreign_keys = ON;
INSERT INTO courses (id, slug, title, description, entitlement_key, published)
VALUES ('small-experiments', 'small-experiments', 'Small Experiments',
  'Make room for one small creative experiment.', 'course:small-experiments', 1)
ON CONFLICT(id) DO NOTHING;

INSERT INTO course_modules (id, course_id, title, position)
VALUES ('getting-started', 'small-experiments', 'Getting started', 0)
ON CONFLICT(id) DO NOTHING;

INSERT INTO course_lessons (id, course_id, module_id, title, kind, position, body_markdown, published)
VALUES ('choose-an-experiment', 'small-experiments', 'getting-started',
  'Choose an experiment', 'exercise', 0,
  'Choose something you can try in an afternoon. What would you like to learn?', 1)
ON CONFLICT(id) DO NOTHING;

INSERT INTO course_lessons (id, course_id, module_id, title, kind, position, body_markdown, published)
VALUES ('reflect-and-repeat', 'small-experiments', 'getting-started',
  'Reflect and repeat', 'text', 1,
  'What surprised you? Write down one thing you would keep and one thing you would change.', 1)
ON CONFLICT(id) DO NOTHING;
