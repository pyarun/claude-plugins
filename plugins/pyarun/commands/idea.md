---
description: Capture an idea from this session into your idea library, or review the library
argument-hint: "[note] | review"
---

# Idea

- `/idea` — pick the strongest idea from this session and file it
- `/idea <note>` — file what the note points at (e.g. `/idea the retry-storm fix is worth a post`)
- `/idea review` — show the library ranked, and recommend what to write next

Arguments: $ARGUMENTS

## Setup check

Read `~/.claude/observer/RULES.md`, `~/.claude/observer/profile.md` and
`~/.claude/observer/config.json`. If any is missing, or the profile still has its bracketed
template lines, tell the user to run `/pyarun:observer-setup` first and stop.

Follow RULES.md and the profile exactly — they define the audience, what counts as an idea,
the types, the privacy rules, duplicate handling and the entry format. The library is the
`library_dir` in config.json (expand `~`).

The nightly observer skips projects in `deny_cwd_prefixes`. `/idea` does not: running it is the
user's explicit choice to record this. The privacy rules still apply in full.

## Capture mode (no argument, or a note)

1. Look back over this conversation. With a note, the note says what to record and the angle;
   without one, choose the single strongest candidate under the baseline filter in RULES.md.
   Record at most two ideas per run.
2. If nothing in the session clears the bar, say so in one line and write nothing.
3. Check the library for duplicates as RULES.md describes; update rather than duplicate.
4. Write the entry with `source: manual`. In `sessions`, use the basename of the current
   working directory, the first 8 characters of this session's id if known (otherwise omit
   it), and today's date.
5. Reply with the file path, the title, the type, the sensitivity and the hook. Nothing else.

## Review mode (`review`)

1. Read the frontmatter of every entry in the library that has a `type` field.
2. Show entries with `status: idea` as a table sorted by `seen` × `score`, highest first:
   title, type, sensitivity, seen, score, last_seen.
3. Recommend the top three publishable ones (`post`, `article`, `talk`, `product`) to draft
   next, one line each on why now.
4. List `learning` and `habit` entries separately — those are for the user, not for publishing.
