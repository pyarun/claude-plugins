---
description: Install or update the work observer — files, profile, and the daily schedule (macOS)
---

# Work observer setup

Run this after installing the plugin, and again after every plugin update: the daily job runs
a copy in `~/.claude/observer/`, so an update only takes effect once this re-copies it.

## 1. Install

Run: `python3 "${CLAUDE_PLUGIN_ROOT}/observer/observer.py" install`

If `${CLAUDE_PLUGIN_ROOT}` was not filled in (the path does not exist), Glob for
`~/.claude/plugins/cache/pyarun-plugins/pyarun/*/observer/observer.py` and use the newest version.

This copies `observer.py` and `RULES.md` into `~/.claude/observer/`, creates `config.json` and
`profile.md` from templates if they do not exist yet (existing ones are never overwritten), and
(re)loads the launchd job.

## 2. Fill in the profile and config (first install only)

If install printed `created … from template`, interview the user one question at a time, then
edit `~/.claude/observer/profile.md` and `~/.claude/observer/config.json`:

1. Name, role, years of experience, deep areas → profile "Who I am".
2. The voices they publish in and the audience for each → profile "Voices and audiences".
3. Titles or claims ideas must avoid → profile "Titles and claims".
4. Clients, topics or projects that must never appear → profile "Off-limits".
5. Project folders the observer must never read (client work, finance) → `deny_cwd_prefixes`.
   Suggest adding the folder of the content project itself, so drafting sessions are not mined.
6. Skills whose sessions must never be read (e.g. a finance skill) → `deny_skills`.
7. Where the idea library lives → `library_dir`.
8. What hour the daily run should happen → `schedule_hour` (0–23, local time). Each run mines
   the previous day, so any hour works; an evening hour when the Mac is awake is best.
9. Email for nudges, or none → `email_to`. Email is sent with Composio's `GMAIL_SEND_EMAIL`, so it
   needs the `composio` CLI logged in with Gmail linked. Read the address back to the user
   character by character before saving it.

If `schedule_hour` changed, run the install command again to reload the schedule.

## 3. Offer a backfill

Claude Code deletes transcripts about 30 days after a session was last used. Offer to capture
what is still there — it is local and costs nothing:

`python3 ~/.claude/observer/observer.py capture --since <date 30 days ago>`

Mining those days costs one headless Claude run per day (about 5 minutes each), so ask before
running `python3 ~/.claude/observer/observer.py spot --since <date>`.

## 4. Confirm

Show `launchctl print gui/$(id -u)/com.claude.work-observer | grep -E "state|Hour"`, the
library path, and how to stop it: `python3 ~/.claude/observer/observer.py uninstall`.
