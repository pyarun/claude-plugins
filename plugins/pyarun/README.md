# pyarun

Arun Mittal's Claude Code toolkit. Every command is namespaced `/pyarun:<command>`.

| Command | What |
|---|---|
| `/pyarun:idea` | Capture an idea from this session, or `review` the library |
| `/pyarun:observer-setup` | Install or update the work observer |

## Work observer

Your best writing material is the work you already did — the bug that wasn't where it looked,
the framework you stopped fighting, the design you threw away. It disappears into session
transcripts that Claude Code deletes after about 30 days.

The work observer reads those sessions once a day and files what is worth sharing into an idea
library: posts, articles, talks, product stories — plus private notes on learning gaps and
habits worth changing. You never have to remember to write anything down.

### How it works

```
 daily, on a schedule                                    any time, in any session
 ─────────────────────────────────────────────────       ─────────────────────────
 1. capture   trim yesterday's transcripts into small     /pyarun:idea          capture now
              digests (local, no AI)                      /pyarun:idea <note>   capture with your angle
 2. spot      headless Claude reads the digests, filters  /pyarun:idea review   ranked library
              against your experience level, files ideas
 3. nudge     macOS notification, optional email
```

- **Ideas are generalized.** Entries carry a sensitivity (`public-safe`, `generalize-first`,
  `private`) and never include customer data, colleagues' names, secrets, internal URLs or
  unreleased plans.
- **Themes rise.** When the same insight comes up on another day, the existing entry is updated
  and its `seen` count grows — recurring themes are the ones worth publishing.
- **Nothing is published for you.** The library is a backlog; drafting and posting stay yours.
- **You choose what it never reads.** Folders and skills on the deny list are skipped entirely.
  `/pyarun:idea` still works there when you explicitly want something recorded.

### Requirements

- macOS (the schedule uses launchd and notifications use `osascript`)
- Python 3.9+ (the one macOS ships is enough)
- Claude Code CLI on `PATH`
- Optional, for email: the [Composio CLI](https://composio.dev) logged in with Gmail linked

### Install

```
/plugin marketplace add pyarun/claude-plugins
/plugin install pyarun@pyarun-plugins
/pyarun:observer-setup
```

Setup copies the observer to `~/.claude/observer/`, interviews you to fill in your profile
(who you are, the voices you publish in, what is off-limits) and schedules the daily run.
After a plugin update, run `/pyarun:observer-setup` again to apply it.

### Files

| Path | What |
|---|---|
| `~/.claude/observer/profile.md` | Who you are and who you write for — edit freely |
| `~/.claude/observer/config.json` | Library path, deny list, schedule hour, model, email |
| `~/.claude/observer/RULES.md` | What counts as an idea and the entry format (replaced on setup) |
| `~/.claude/observer/digests/` | Trimmed per-day session digests |
| `~/.claude/observer/nightly.log` | Output of each daily run |

### Commands

```
python3 ~/.claude/observer/observer.py capture --since 2026-01-01   # digest older sessions
python3 ~/.claude/observer/observer.py spot --since 2026-01-01      # mine them (one Claude run per day)
python3 ~/.claude/observer/observer.py uninstall                    # stop the schedule, keep data
```

### Cost

Capture is local and free. Spotting is one headless Claude run per day of work — about five
minutes on Sonnet for a busy day of 20–40 sessions. Change `spot_model` in config.json to trade
cost for judgment.
