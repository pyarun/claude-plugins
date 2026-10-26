from __future__ import annotations

import argparse
import json
import plistlib
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path

OBSERVER_DIR = Path.home() / ".claude" / "observer"
PROJECTS_DIR = Path.home() / ".claude" / "projects"
DIGESTS_DIR = OBSERVER_DIR / "digests"
STATE_FILE = OBSERVER_DIR / "state.json"
CONFIG_FILE = OBSERVER_DIR / "config.json"
PROFILE_FILE = OBSERVER_DIR / "profile.md"
LAUNCHD_LABEL = "com.claude.work-observer"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


@cache
def config() -> dict:
    raw = json.loads(CONFIG_FILE.read_text())
    return {
        **raw,
        "library_dir": str(Path(raw["library_dir"]).expanduser()),
        "deny_cwd_prefixes": [str(Path(p).expanduser()) for p in raw["deny_cwd_prefixes"]],
    }


@dataclass
class Turn:
    user: str
    claude: str = ""


@dataclass
class Day:
    turns: list[Turn] = field(default_factory=list)
    files: set[str] = field(default_factory=set)
    prs: set[str] = field(default_factory=set)


class Capture:
    """Trims raw session transcripts into small per-day digests the spot run can afford to read."""

    NOISE_TAGS = (
        "system-reminder", "browser_instruction", "ide_opened_file", "ide_selection",
        "local-command-caveat", "local-command-stdout", "local-command-stderr",
        "command-message", "command-name", "command-args",
    )
    EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
    USER_CHARS = 1200
    CLAUDE_CHARS = 900
    MAX_TURNS = 24

    @staticmethod
    def run(since: datetime) -> int:
        written = 0
        for path in PROJECTS_DIR.glob("*/*.jsonl"):
            if path.name.startswith("agent-") or datetime.fromtimestamp(path.stat().st_mtime) < since:
                continue
            parsed = Capture.parse(path)
            if parsed is None:
                continue
            meta, days = parsed
            for day, digest in days.items():
                out = DIGESTS_DIR / day.isoformat() / f"{meta['session']}.md"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(Capture.render(meta, day, digest))
                written += 1
        return written

    @staticmethod
    def parse(path: Path) -> tuple[dict, dict[date, Day]] | None:
        meta = {"session": path.stem, "cwd": "", "branch": "", "title": ""}
        days: dict[date, Day] = {}
        current: Turn | None = None
        for line in path.open():
            entry = json.loads(line)
            kind = entry.get("type")
            if kind == "ai-title":
                meta["title"] = entry["aiTitle"]
                continue
            if entry.get("isSidechain") or "timestamp" not in entry:
                continue
            # Python < 3.11 cannot parse the trailing "Z" that transcripts use.
            day = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")).astimezone().date()
            bucket = days.setdefault(day, Day())
            if kind == "pr-link":
                bucket.prs.add(entry["prUrl"])
                continue
            if kind not in ("user", "assistant") or not isinstance(entry.get("message"), dict):
                continue
            meta["cwd"] = meta["cwd"] or entry.get("cwd", "")
            meta["branch"] = entry.get("gitBranch", meta["branch"])
            content = entry["message"]["content"]
            blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
            if kind == "user":
                if entry.get("isMeta"):
                    continue
                text = Capture.clean(" ".join(b["text"] for b in blocks if b.get("type") == "text"))
                if text and not text.startswith(("[Request interrupted", "Base directory for this skill")):
                    current = Turn(user=text[: Capture.USER_CHARS])
                    bucket.turns.append(current)
                continue
            for block in blocks:
                if block.get("type") == "text" and current is not None:
                    current.claude = block["text"][: Capture.CLAUDE_CHARS]
                elif block.get("type") == "tool_use":
                    name, args = block["name"], block.get("input", {})
                    if name == "Skill" and args.get("skill", "").split(":")[-1] in config()["deny_skills"]:
                        return None
                    if name in Capture.EDIT_TOOLS and "file_path" in args:
                        bucket.files.add(args["file_path"])
        if Capture.denied(meta["cwd"]):
            return None
        return meta, {d: b for d, b in days.items() if b.turns}

    @staticmethod
    def denied(cwd: str) -> bool:
        # The observer's own headless spot runs write transcripts too; never feed them back in.
        prefixes = [str(OBSERVER_DIR), *config()["deny_cwd_prefixes"]]
        return not cwd or any(Path(cwd).is_relative_to(p) for p in prefixes)

    @staticmethod
    def clean(text: str) -> str:
        command = re.search(r"<command-name>(.*?)</command-name>", text, re.S)
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
        for tag in Capture.NOISE_TAGS:
            text = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", "", text, flags=re.S)
        text = text.strip()
        if command and not text:
            text = f"{command.group(1).strip()} {args.group(1).strip() if args else ''}".strip()
        return text

    @staticmethod
    def render(meta: dict, day: date, digest: Day) -> str:
        turns = digest.turns
        omitted = len(turns) - Capture.MAX_TURNS
        if omitted > 0:
            half = Capture.MAX_TURNS // 2
            turns = [*turns[:half], Turn(user=f"[… {omitted} turns omitted …]"), *turns[-half:]]
        lines = [
            f"# {meta['title'] or 'Untitled session'}",
            f"project: {meta['cwd']}  branch: {meta['branch']}  session: {meta['session'][:8]}  date: {day}",
        ]
        if digest.files:
            lines.append(f"files changed: {', '.join(sorted(Path(f).name for f in digest.files))}")
        if digest.prs:
            lines.append(f"PRs: {', '.join(sorted(digest.prs))}")
        for turn in turns:
            lines += ["", f"**User:** {turn.user}"]
            if turn.claude:
                lines.append(f"**Claude:** {turn.claude}")
        return "\n".join(lines) + "\n"


class Spot:
    """Runs headless Claude over one day of digests to find ideas and file them in the library."""

    RESULT_SCHEMA = {
        "type": "object",
        "required": ["added", "updated"],
        "properties": {
            "added": {"type": "array", "items": {
                "type": "object", "required": ["title", "type", "hook", "file"],
                "properties": {k: {"type": "string"} for k in ("title", "type", "hook", "file")},
            }},
            "updated": {"type": "array", "items": {
                "type": "object", "required": ["title", "file"],
                "properties": {k: {"type": "string"} for k in ("title", "file")},
            }},
        },
    }

    @staticmethod
    def pending(since: date) -> list[date]:
        done = set(Spot.state()["spotted"])
        today = date.today()
        return sorted(
            day for day in (date.fromisoformat(p.name) for p in DIGESTS_DIR.iterdir() if p.is_dir())
            if since <= day < today and day.isoformat() not in done
        )

    @staticmethod
    def state() -> dict:
        return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"spotted": []}

    @staticmethod
    def run_day(day: date) -> dict | None:
        library = config()["library_dir"]
        Path(library).mkdir(parents=True, exist_ok=True)
        prompt = (
            f"Spot run for {day}. Read {OBSERVER_DIR / 'RULES.md'} and {PROFILE_FILE} first and follow them exactly.\n"
            f"Session digests for that day: {DIGESTS_DIR / day.isoformat()}/ (one file per session).\n"
            f"Idea library: {library}\n"
            f"New entries get `source: auto`. Today is {date.today()}.\n"
            "Finish by reporting every entry you added or updated."
        )
        proc = subprocess.run(
            [
                shutil.which("claude") or "claude", "-p", prompt,
                "--model", config()["spot_model"],
                "--output-format", "json",
                "--json-schema", json.dumps(Spot.RESULT_SCHEMA),
                "--allowedTools", "Read,Write,Edit,Glob,Grep",
                "--add-dir", library, str(DIGESTS_DIR),
            ],
            cwd=OBSERVER_DIR, capture_output=True, text=True, check=True, timeout=1800,
        )
        reply = json.loads(proc.stdout)
        if reply["is_error"] or "structured_output" not in reply:
            print(f"spot {day} failed, will retry next run: {reply['subtype']} {reply.get('result', '')[:300]}")
            return None
        state = Spot.state()
        state["spotted"] = sorted({*state["spotted"], day.isoformat()})
        STATE_FILE.write_text(json.dumps(state, indent=2))
        return reply["structured_output"]

    @staticmethod
    def run_since(since: date) -> tuple[list[dict], list[dict]]:
        added: list[dict] = []
        updated: list[dict] = []
        for day in Spot.pending(since):
            result = Spot.run_day(day)
            if result is None:
                continue
            added += result["added"]
            updated += result["updated"]
            print(f"spotted {day}: {len(result['added'])} added, {len(result['updated'])} updated")
        return added, updated


class Nudge:
    @staticmethod
    def send(added: list[dict], updated: list[dict]) -> None:
        if not added and not updated:
            return
        summary = f"{len(added)} new idea(s), {len(updated)} seen again"
        subprocess.run(
            ["osascript", "-e", f'display notification "{summary}" with title "Idea library"'],
            check=True,
        )
        if config()["email_to"]:
            Nudge.email(f"Idea library: {summary}", Nudge.body(added, updated))

    @staticmethod
    def body(added: list[dict], updated: list[dict]) -> str:
        lines = [f"Ideas spotted in your work. Library: {config()['library_dir']}", ""]
        for idea in added:
            lines += [f"[{idea['type']}] {idea['title']}", f"  {idea['hook']}", f"  {idea['file']}", ""]
        if updated:
            lines += ["Seen again (themes getting stronger):", *(f"- {idea['title']}" for idea in updated)]
        return "\n".join(lines)

    @staticmethod
    def email(subject: str, body: str) -> None:
        composio = shutil.which("composio") or str(Path.home() / ".composio" / "composio")
        payload = {"recipient_email": config()["email_to"], "subject": subject, "body": body}
        subprocess.run([composio, "execute", "GMAIL_SEND_EMAIL", "-d", json.dumps(payload)], check=True)


class Installer:
    """Copies the observer out of the versioned plugin cache and schedules it with launchd."""

    SOURCE_DIR = Path(__file__).resolve().parent

    @staticmethod
    def install() -> None:
        OBSERVER_DIR.mkdir(parents=True, exist_ok=True)
        if Installer.SOURCE_DIR != OBSERVER_DIR:
            for name in ("observer.py", "RULES.md"):
                shutil.copy2(Installer.SOURCE_DIR / name, OBSERVER_DIR / name)
        for target, example in ((CONFIG_FILE, "config.example.json"), (PROFILE_FILE, "profile.example.md")):
            if not target.exists():
                shutil.copy2(Installer.SOURCE_DIR / example, target)
                print(f"created {target} from template")
        tool_dirs = {str(Path(found).parent) for found in map(shutil.which, ("claude", "composio")) if found}
        plist = {
            "Label": LAUNCHD_LABEL,
            # Resolved via PATH rather than sys.executable: a versioned interpreter path such as
            # Homebrew's python@3.14 disappears on the next minor upgrade; /usr/bin/python3 is the fallback.
            "ProgramArguments": ["/usr/bin/env", "python3", str(OBSERVER_DIR / "observer.py"), "nightly"],
            "EnvironmentVariables": {"PATH": ":".join([*sorted(tool_dirs), "/usr/local/bin", "/usr/bin", "/bin"])},
            "StartCalendarInterval": {"Hour": config()["schedule_hour"], "Minute": 0},
            "StandardOutPath": str(OBSERVER_DIR / "nightly.log"),
            "StandardErrorPath": str(OBSERVER_DIR / "nightly.log"),
        }
        Installer.unload()
        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        PLIST_PATH.write_bytes(plistlib.dumps(plist))
        subprocess.run(["launchctl", "bootstrap", Installer.domain(), str(PLIST_PATH)], check=True)
        print(f"scheduled daily at {config()['schedule_hour']:02d}:00 as {LAUNCHD_LABEL}")

    @staticmethod
    def uninstall() -> None:
        Installer.unload()
        PLIST_PATH.unlink(missing_ok=True)
        print(f"schedule removed; data kept in {OBSERVER_DIR}")

    @staticmethod
    def unload() -> None:
        loaded = subprocess.run(["launchctl", "print", f"{Installer.domain()}/{LAUNCHD_LABEL}"], capture_output=True)
        if loaded.returncode == 0:
            subprocess.run(["launchctl", "bootout", f"{Installer.domain()}/{LAUNCHD_LABEL}"], check=True)

    @staticmethod
    def domain() -> str:
        return f"gui/{subprocess.run(['id', '-u'], capture_output=True, text=True, check=True).stdout.strip()}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe Claude Code sessions and build an idea library.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install", help="copy files to ~/.claude/observer and schedule the daily run")
    sub.add_parser("uninstall", help="remove the daily schedule, keep all data")
    sub.add_parser("nightly", help="capture recent sessions, spot ideas, notify")
    capture = sub.add_parser("capture", help="write digests for transcripts changed since a date")
    capture.add_argument("--since", type=date.fromisoformat, required=True)
    spot = sub.add_parser("spot", help="spot ideas for unspotted days since a date (no notification)")
    spot.add_argument("--since", type=date.fromisoformat, required=True)
    args = parser.parse_args()

    if args.command == "install":
        Installer.install()
    elif args.command == "uninstall":
        Installer.uninstall()
    elif args.command == "nightly":
        since = datetime.now() - timedelta(days=config()["lookback_days"])
        print(f"{datetime.now():%Y-%m-%d %H:%M} captured {Capture.run(since)} digest(s)")
        Nudge.send(*Spot.run_since(since.date()))
    elif args.command == "capture":
        print(f"captured {Capture.run(datetime.combine(args.since, datetime.min.time()))} digest(s)")
    else:
        Spot.run_since(args.since)


if __name__ == "__main__":
    main()
