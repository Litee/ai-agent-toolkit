#!/usr/bin/env python3
"""Skill issue tracker CLI.

Manage skill bug reports and feature requests stored as JSON files under
<db-root>/<skill-name>/<0001>-<slug>.json.

Subcommands:
  create    Create a new issue
  show      Show a single issue with comments
  list      List issues, with optional filters
  update    Update issue fields (status, title, description)
  comment   Add a comment to an issue
  search    Search issues by text

Global options (before subcommand):
  --txt     Output human-readable text instead of JSON (default: JSON)

Usage examples:
  python3 skill_issues.py --db-root /path/to/tracker create --skill my-auth-plugin --skill-version 1.2.0 --title "Bug title" --description "Details"
  python3 skill_issues.py --db-root /path/to/tracker list --skill my-auth-plugin --status open pending
  python3 skill_issues.py --db-root /path/to/tracker show --skill my-auth-plugin --id 3
  python3 skill_issues.py --db-root /path/to/tracker update --skill my-auth-plugin --id 3 --status done
  python3 skill_issues.py --db-root /path/to/tracker comment --skill my-auth-plugin --id 3 --text "Fixed in abc123"
  python3 skill_issues.py --db-root /path/to/tracker search --query "timeout"
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

VALID_STATUSES = ("open", "in_progress", "done", "wont_fix")
ID_WIDTH = 4  # zero-padded to 4 digits: 0001, 0002, ...
SLUG_LENGTH = 30  # max characters in filename slug derived from title


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class IssueError(Exception):
    pass


class IssueNotFoundError(IssueError):
    pass


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

_db_root_path: str = ""


def _db_root() -> str:
    return _db_root_path


def _skill_dir(skill: str) -> str:
    return os.path.join(_db_root(), skill)


def _id_str(issue_id: int) -> str:
    """Format issue ID as zero-padded string, e.g. 1 -> '0001'."""
    return str(issue_id).zfill(ID_WIDTH)


def _title_slug(title: str) -> str:
    """Derive a filesystem-safe slug of exactly SLUG_LENGTH chars from title."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:SLUG_LENGTH].rstrip("-")


def _issue_filename(issue_id: int, title: str) -> str:
    return f"{_id_str(issue_id)}-{_title_slug(title)}.json"


def _issue_path(skill: str, issue_id: int, title: str) -> str:
    return os.path.join(_skill_dir(skill), _issue_filename(issue_id, title))


def _find_issue_path(skill: str, issue_id) -> str:
    """Locate an existing issue file by ID prefix, regardless of slug."""
    skill_dir = _skill_dir(skill)
    prefix = _id_str(int(issue_id)) + "-"
    if os.path.isdir(skill_dir):
        for fname in os.listdir(skill_dir):
            if fname.startswith(prefix) and fname.endswith(".json"):
                return os.path.join(skill_dir, fname)
    raise IssueNotFoundError(f"Issue #{_id_str(int(issue_id))} not found for skill '{skill}'")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_ISSUE_FNAME_RE = re.compile(r"^(\d{4})-[a-z0-9-]+\.json$")


def _next_id(skill: str) -> int:
    """Scan skill dir for the highest zero-padded ID, return max + 1."""
    skill_dir = _skill_dir(skill)
    if not os.path.isdir(skill_dir):
        return 1
    max_id = 0
    for fname in os.listdir(skill_dir):
        m = _ISSUE_FNAME_RE.match(fname)
        if m:
            max_id = max(max_id, int(m.group(1)))
    return max_id + 1


def _load_issue(skill: str, issue_id: int) -> dict:
    path = _find_issue_path(skill, issue_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_issue(issue: dict) -> None:
    skill_dir = _skill_dir(issue["skill"])
    os.makedirs(skill_dir, exist_ok=True)
    new_path = _issue_path(issue["skill"], int(issue["id"]), issue["title"])
    # If the file was renamed (e.g. title changed), remove the old file
    try:
        old_path = _find_issue_path(issue["skill"], int(issue["id"]))
        if old_path != new_path and os.path.isfile(old_path):
            os.remove(old_path)
    except IssueNotFoundError:
        pass
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(issue, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _load_all_issues(skill: Optional[str] = None, statuses: Optional[list] = None) -> list:
    """Load all issues, optionally filtered by skill and/or status list."""
    db = _db_root()
    results = []

    if skill:
        skill_dirs = [skill] if os.path.isdir(_skill_dir(skill)) else []
    else:
        if not os.path.isdir(db):
            return []
        skill_dirs = [d for d in os.listdir(db) if os.path.isdir(os.path.join(db, d))]

    for sk in sorted(skill_dirs):
        sk_dir = _skill_dir(sk)
        fnames = sorted(
            (f for f in os.listdir(sk_dir) if _ISSUE_FNAME_RE.match(f)),
            key=lambda n: int(_ISSUE_FNAME_RE.match(n).group(1)),  # type: ignore[union-attr]
        )
        for fname in fnames:
            path = os.path.join(sk_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    issue = json.load(f)
                if statuses and issue.get("status") not in statuses:
                    continue
                results.append(issue)
            except (json.JSONDecodeError, OSError):
                pass

    return results


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _print_issue(issue: dict) -> None:
    label_w = 14
    print(f"{'Issue:':<{label_w}} #{issue['id']}")
    print(f"{'Title:':<{label_w}} {issue['title']}")
    print(f"{'Skill:':<{label_w}} {issue['skill']}")
    print(f"{'Version:':<{label_w}} {issue.get('skill_version', '(unknown)')}")
    print(f"{'Status:':<{label_w}} {issue['status']}")
    print(f"{'Created:':<{label_w}} {issue['created_at']}")
    print(f"{'Updated:':<{label_w}} {issue['updated_at']}")
    print()
    print("Description:")
    for line in issue.get("description", "").splitlines():
        print(f"  {line}")
    comments = issue.get("comments", [])
    print()
    print(f"Comments ({len(comments)}):")
    if not comments:
        print("  (none)")
    for c in comments:
        print(f"  [{c['created_at']}]")
        for line in c["text"].splitlines():
            print(f"    {line}")


def _print_issue_table(issues: list) -> None:
    if not issues:
        print("No issues found.")
        return
    id_w, skill_w, status_w = 4, 50, 10
    print(f"{'ID':<{id_w}}  {'Skill':<{skill_w}}  {'Status':<{status_w}}  Title")
    print("-" * (id_w + 2 + skill_w + 2 + status_w + 2 + 50))
    for issue in issues:
        iid = f"#{issue['id']}"
        sk = issue["skill"]
        if len(sk) > skill_w:
            sk = sk[: skill_w - 1] + "."
        st = issue["status"]
        title = issue["title"]
        if len(title) > 60:
            title = title[:57] + "..."
        print(f"{iid:<{id_w}}  {sk:<{skill_w}}  {st:<{status_w}}  {title}")


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_create(args: argparse.Namespace) -> None:
    now = _now()
    issue_id = _next_id(args.skill)
    issue = {
        "id": _id_str(issue_id),
        "title": args.title,
        "skill": args.skill,
        "skill_version": args.skill_version,
        "status": args.status,
        "created_at": now,
        "updated_at": now,
        "description": args.description,
        "comments": [],
    }
    _save_issue(issue)
    if args.json:
        print(json.dumps(issue, indent=2))
    else:
        print(f"Created issue #{_id_str(issue_id)} for skill '{args.skill}'")


def cmd_show(args: argparse.Namespace) -> None:
    issue = _load_issue(args.skill, args.id)
    if args.json:
        print(json.dumps(issue, indent=2))
    else:
        _print_issue(issue)


def cmd_list(args: argparse.Namespace) -> None:
    issues = _load_all_issues(
        skill=args.skill or None,
        statuses=args.status or None,
    )
    if args.json:
        print(json.dumps(issues, indent=2))
    else:
        _print_issue_table(issues)


def cmd_update(args: argparse.Namespace) -> None:
    if not any([args.status, args.title, args.description]):
        print("Error: at least one of --status, --title, or --description is required.", file=sys.stderr)
        sys.exit(1)
    issue = _load_issue(args.skill, args.id)
    if args.status:
        issue["status"] = args.status
    if args.title:
        issue["title"] = args.title
    if args.description:
        issue["description"] = args.description
    issue["updated_at"] = _now()
    _save_issue(issue)
    if args.json:
        print(json.dumps(issue, indent=2))
    else:
        print(f"Updated issue #{_id_str(args.id)} for skill '{args.skill}'")


def cmd_comment(args: argparse.Namespace) -> None:
    issue = _load_issue(args.skill, args.id)
    comment = {"text": args.text, "created_at": _now()}
    issue.setdefault("comments", []).append(comment)
    issue["updated_at"] = _now()
    _save_issue(issue)
    if args.json:
        print(json.dumps(issue, indent=2))
    else:
        print(f"Added comment to issue #{_id_str(args.id)} for skill '{args.skill}'")


def cmd_search(args: argparse.Namespace) -> None:
    query = args.query.lower()
    issues = _load_all_issues(
        skill=args.skill or None,
        statuses=args.status or None,
    )
    matches = []
    for issue in issues:
        haystack = " ".join([
            issue.get("title", ""),
            issue.get("skill_version", ""),
            issue.get("description", ""),
            " ".join(c.get("text", "") for c in issue.get("comments", [])),
        ]).lower()
        if query in haystack:
            matches.append(issue)
    if args.json:
        print(json.dumps(matches, indent=2))
    else:
        _print_issue_table(matches)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _add_json(p: argparse.ArgumentParser) -> None:
    p.add_argument("--txt", dest="json", action="store_false",
                   help="Output human-readable text instead of JSON (default: JSON)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill_issues.py",
        description="Manage skill issue reports and feature requests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            '  %(prog)s --db-root /path/to/tracker create --skill my-auth-plugin --skill-version 1.2.0 --title "Bug title" --description "Details"\n'
            "  %(prog)s --db-root /path/to/tracker list --skill my-auth-plugin\n"
            "  %(prog)s --db-root /path/to/tracker list --status open pending\n"
            "  %(prog)s --db-root /path/to/tracker list\n"
            "  %(prog)s --db-root /path/to/tracker show --skill my-auth-plugin --id 3\n"
            "  %(prog)s --db-root /path/to/tracker update --skill my-auth-plugin --id 3 --status done\n"
            '  %(prog)s --db-root /path/to/tracker comment --skill my-auth-plugin --id 3 --text "Fixed in abc123"\n'
            '  %(prog)s --db-root /path/to/tracker search --query "timeout"\n'
            "  %(prog)s --db-root /path/to/tracker search --query \"fetch\" --skill my-data-fetcher\n"
        ),
    )
    parser.add_argument(
        "--db-root",
        required=True,
        metavar="PATH",
        help="Root directory for issue storage",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p = subparsers.add_parser("create", help="Create a new issue")
    p.add_argument("--skill", required=True, help="Skill name (no plugin prefix)")
    p.add_argument("--skill-version", required=True, dest="skill_version",
                   help="Version of the skill the issue was observed on (e.g. 1.2.0)")
    p.add_argument("--title", required=True, help="Issue title")
    p.add_argument("--description", required=True, help="Issue description (markdown)")
    p.add_argument("--status", default="open", choices=VALID_STATUSES,
                   help="Initial status (default: open)")
    _add_json(p)

    # show
    p = subparsers.add_parser("show", help="Show a single issue with comments")
    p.add_argument("--skill", required=True, help="Skill name")
    p.add_argument("--id", required=True, type=int, help="Issue ID")
    _add_json(p)

    # list
    p = subparsers.add_parser("list", help="List issues with optional filters")
    p.add_argument("--skill", help="Filter by skill name")
    p.add_argument("--status", nargs="+", metavar="STATUS", choices=VALID_STATUSES,
                   help="Filter by status(es): open in_progress done wont_fix")
    _add_json(p)

    # update
    p = subparsers.add_parser("update", help="Update issue fields")
    p.add_argument("--skill", required=True, help="Skill name")
    p.add_argument("--id", required=True, type=int, help="Issue ID")
    p.add_argument("--status", choices=VALID_STATUSES, help="New status")
    p.add_argument("--title", help="New title")
    p.add_argument("--description", help="New description")
    _add_json(p)

    # comment
    p = subparsers.add_parser("comment", help="Add a comment to an issue")
    p.add_argument("--skill", required=True, help="Skill name")
    p.add_argument("--id", required=True, type=int, help="Issue ID")
    p.add_argument("--text", required=True, help="Comment text (markdown)")
    _add_json(p)

    # search
    p = subparsers.add_parser("search", help="Search issues by text")
    p.add_argument("--query", required=True, help="Case-insensitive substring to search for")
    p.add_argument("--skill", help="Restrict search to one skill")
    p.add_argument("--status", nargs="+", metavar="STATUS", choices=VALID_STATUSES,
                   help="Filter by status(es)")
    _add_json(p)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_HANDLERS = {
    "create": cmd_create,
    "show": cmd_show,
    "list": cmd_list,
    "update": cmd_update,
    "comment": cmd_comment,
    "search": cmd_search,
}


def main() -> None:
    global _db_root_path
    parser = build_parser()
    args = parser.parse_args()
    _db_root_path = os.path.expanduser(args.db_root)

    handler = _HANDLERS.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args)
    except IssueNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except IssueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
