# Idea Library — Rules

Shared by the nightly spot run and the `/idea` command. Both write to the same
library, so both follow this file exactly.

Read `~/.claude/observer/profile.md` alongside this file. The profile says who
the user is, which voices they publish in, for which audiences, and anything
extra that is off-limits. Where the profile and this file disagree, the
profile wins.

## What counts as an idea (the baseline filter)

Judge novelty against the experience level in the profile. Work that is
routine for someone at that level is NOT an idea: CRUD, standard framework
patterns, ordinary bug fixes, dependency bumps, config changes, routine
deploys, plain refactors.

An idea needs at least one of:

- **A story arc** — tried X, it failed or hit a wall, switched to Y, and why.
  These are the strongest material; look for them first.
- **A non-obvious root cause** — the bug was not where it looked.
- **A trade-off decision** with the alternatives and why one won.
- **A measured number** — before/after, cost, latency, scale.
- **An opinion** formed from experience that a peer might disagree with.
- **A way of working with AI coding agents** that others could copy.
- **A shipped product capability** with a clear user problem it solves, if
  the profile includes a product-marketing voice.

Fewer, stronger ideas beat a long list. A day with nothing worth recording is
normal — write nothing.

## Types

| type | meaning |
|---|---|
| `post` | Fits a LinkedIn post: one insight, one story, under 300 words |
| `article` | Needs depth: a blog article, a walkthrough or a deep dive |
| `talk` | Strong enough for a meetup or conference talk |
| `product` | Product-marketing angle: a feature story for users |
| `learning` | A gap the user hit that is worth studying properly |
| `habit` | A recurring way they work that costs them time, or a correction they keep repeating |

`learning` and `habit` are for the user only, never for publishing. A `habit`
needs evidence from at least two sessions; one occurrence is not a habit.

## Privacy

Every entry gets one `sensitivity`:

- `public-safe` — nothing identifying; can be published as written.
- `generalize-first` — the lesson is public but the details are internal.
  Write the entry already generalized: the lesson, not the incident.
- `private` — useful to the user but not for publishing.

Never put any of these in an entry, whatever the sensitivity:

- customer or user names, data, or counts
- revenue, pricing negotiations, contract terms, salaries
- unreleased roadmap or dates
- unpatched security issues
- colleagues by name, or criticism of colleagues
- secrets, keys, tokens, internal URLs, hostnames
- anything the profile lists as off-limits

Product names and shipped, public features are fine.

## Before writing: check for duplicates

List and skim the library first (Glob `*.md`, read frontmatter). If an idea
already covers the same insight, update that file instead of creating a new
one: append the session to `sessions`, set `last_seen`, and add any new
evidence. `seen` counts distinct days in `sessions`, not sessions — parallel
worktrees on one task are one sighting. An idea seen on many days is a theme —
that is the signal it is worth publishing.

## Entry format

File name: `YYYY-MM-DD-short-slug.md` (date first seen). One idea per file.

```markdown
---
title: Short title stating the insight, not the topic
type: post | article | talk | product | learning | habit
sensitivity: public-safe | generalize-first | private
status: idea
score: 1-5
seen: 1
first_seen: YYYY-MM-DD
last_seen: YYYY-MM-DD
source: auto | manual
sessions:
  - <project> <session-id-first-8-chars> YYYY-MM-DD
---

**Hook:** one sentence that would stop the target reader scrolling.

## What happened
The situation and the arc, specific enough to write from later. Generalized
if sensitivity is `generalize-first`.

## Takeaway
The portable lesson — what a peer facing the same situation should do.

## Evidence
Short quotes or facts from the session that anchor this in reality.

## Angle
For publishable types: who it is for and how to frame it. For `learning`:
what to study. For `habit`: what to change.
```

`score` is your honest strength rating: 5 = would clearly perform, 3 = solid
but ordinary, 1 = marginal. Do not write anything you would score below 3,
except `learning` and `habit` entries.

Never change `status` on an existing entry; the user moves ideas through the
pipeline themselves.

Write only idea entries in the library — no notes, scratch or placeholder
files. The spot run has no tool that can delete or rename a file, so a file
created by mistake stays there; correct the existing entry in place instead.
