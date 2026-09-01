#!/usr/bin/env python3
"""Import Circle CSV exports into a portable SQLite/D1-shaped database."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "community.sql"
KINDS = ("members", "spaces", "posts", "comments", "events")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", required=True, help="Directory containing Circle CSV files.")
    parser.add_argument("--db", required=True, help="SQLite database to create or update.")
    parser.add_argument(
        "--community-key",
        required=True,
        help="Stable non-secret namespace, normally the community domain or slug.",
    )
    for kind in KINDS:
        parser.add_argument(f"--{kind}", help=f"Explicit {kind} CSV path (optional).")
    parser.add_argument("--schema", default=str(SCHEMA_PATH), help="SQLite schema path.")
    parser.add_argument("--report", help="Optional non-PII JSON report path.")
    parser.add_argument("--reset", action="store_true", help="Delete the destination DB before import.")
    args = parser.parse_args()

    export_dir = Path(args.export_dir).expanduser().resolve()
    db_path = Path(args.db).expanduser().resolve()
    schema_path = Path(args.schema).expanduser().resolve()
    if not export_dir.is_dir():
        raise SystemExit(f"Export directory not found: {export_dir}")
    if not schema_path.is_file():
        raise SystemExit(f"Schema not found: {schema_path}")

    paths = resolve_csv_paths(export_dir, args)
    if not paths.get("members"):
        raise SystemExit(
            "A members CSV is required. Name it with 'members'/'audience' or pass --members PATH."
        )

    if args.reset and db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"community:{args.community_key.strip().lower()}")
    source_digest = digest_files(paths.values())
    batch_id = str(uuid.uuid5(namespace, f"circle-batch:{source_digest}"))
    report: dict[str, Any] = {
        "batch_id": batch_id,
        "community_key": args.community_key,
        "source_digest": source_digest,
        "files": {kind: path.name if path else None for kind, path in paths.items()},
        "counts": {},
        "warnings": {},
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        prepare_batch(conn, batch_id, args.community_key, source_digest, export_dir)

        known_spaces = import_spaces(conn, paths.get("spaces"), batch_id, report)
        for kind in ("posts", "comments", "events"):
            report["counts"][f"raw_{kind}"] = import_raw_content(
                conn, kind, paths.get(kind), batch_id
            )
        import_members(
            conn=conn,
            path=paths["members"],
            batch_id=batch_id,
            namespace=namespace,
            known_spaces=known_spaces,
            report=report,
        )
        conn.commit()
    finally:
        conn.close()

    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Imported Circle batch: {batch_id}")
    print(f"Database: {db_path}")
    for key, value in sorted(report["counts"].items()):
        print(f"{key}: {value}")
    for key, value in sorted(report["warnings"].items()):
        if value:
            print(f"warning.{key}: {value}")


def resolve_csv_paths(export_dir: Path, args: argparse.Namespace) -> dict[str, Path | None]:
    paths: dict[str, Path | None] = {}
    for kind in KINDS:
        explicit = getattr(args, kind)
        if explicit:
            path = Path(explicit).expanduser().resolve()
            if not path.is_file():
                raise SystemExit(f"{kind.title()} CSV not found: {path}")
            paths[kind] = path
        else:
            paths[kind] = discover_csv(export_dir, kind)
    return paths


def discover_csv(export_dir: Path, kind: str) -> Path | None:
    csvs = sorted(path for path in export_dir.rglob("*.csv") if path.is_file())
    tokens = {
        "members": ("members", "member", "audience"),
        "spaces": ("spaces", "space"),
        "posts": ("posts", "post"),
        "comments": ("comments", "comment"),
        "events": ("events", "event"),
    }[kind]
    candidates = []
    for path in csvs:
        stem = path.stem.lower()
        if not any(token in stem for token in tokens):
            continue
        if kind == "members" and any(
            token in stem for token in ("space_member", "event_attendee", "live_participant")
        ):
            continue
        candidates.append(path)

    if not candidates:
        return None
    exact = [path for path in candidates if re.search(rf"(^|[_ -]){kind}($|[_ -])", path.stem.lower())]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    options = "\n  ".join(str(path) for path in candidates)
    raise SystemExit(f"Multiple {kind} CSV candidates found; pass --{kind} explicitly:\n  {options}")


def digest_files(paths: Iterable[Path | None]) -> str:
    digest = hashlib.sha256()
    for path in sorted((path for path in paths if path), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()


def prepare_batch(
    conn: sqlite3.Connection,
    batch_id: str,
    community_key: str,
    source_digest: str,
    export_dir: Path,
) -> None:
    conn.execute(
        """
        INSERT INTO circle_import_batches (id, community_key, source_digest, source_path)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET imported_at = datetime('now')
        """,
        (batch_id, community_key, source_digest, str(export_dir)),
    )
    conn.execute("DELETE FROM member_import_sources WHERE import_batch_id = ?", (batch_id,))
    for table in (
        "circle_raw_members",
        "circle_raw_spaces",
        "circle_raw_posts",
        "circle_raw_comments",
        "circle_raw_events",
    ):
        conn.execute(f"DELETE FROM {table} WHERE import_batch_id = ?", (batch_id,))


def read_csv_dicts(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.reader(source)
        try:
            raw_headers = next(reader)
        except StopIteration:
            return [], []
        headers = dedupe_headers(raw_headers)
        rows = []
        for values in reader:
            row = {
                header: values[index] if index < len(values) else ""
                for index, header in enumerate(headers)
            }
            rows.append(row)
        return headers, rows


def dedupe_headers(headers: list[str]) -> list[str]:
    counts: Counter[str] = Counter()
    unique = []
    for raw_header in headers:
        header = clean(raw_header)
        counts[header] += 1
        unique.append(header if counts[header] == 1 else f"{header}__{counts[header]}")
    return unique


def import_spaces(
    conn: sqlite3.Connection,
    path: Path | None,
    batch_id: str,
    report: dict[str, Any],
) -> set[str]:
    if not path:
        report["counts"]["raw_spaces"] = 0
        report["counts"]["spaces"] = conn.execute("SELECT count(*) FROM circle_spaces").fetchone()[0]
        return {row[0] for row in conn.execute("SELECT name FROM circle_spaces")}

    _, rows = read_csv_dicts(path)
    names: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        space_id = first(row, "ID", "Space ID", "UID") or f"derived:{slugify(first(row, 'Name') or str(row_number))}"
        name = first(row, "Name", "Space Name", "Title") or f"Unnamed space {row_number}"
        conn.execute(
            """
            INSERT INTO circle_raw_spaces (import_batch_id, row_number, circle_space_id, raw_json)
            VALUES (?, ?, ?, ?)
            """,
            (batch_id, row_number, space_id, json_dumps(row)),
        )
        conn.execute(
            """
            INSERT INTO circle_spaces (
              circle_space_id, name, slug, is_private, is_hidden_from_non_members, source
            ) VALUES (?, ?, ?, ?, ?, 'spaces_csv')
            ON CONFLICT(circle_space_id) DO UPDATE SET
              name = excluded.name,
              slug = excluded.slug,
              is_private = excluded.is_private,
              is_hidden_from_non_members = excluded.is_hidden_from_non_members,
              source = excluded.source,
              imported_at = datetime('now')
            """,
            (
                space_id,
                name,
                first(row, "Slug") or slugify(name),
                bool_to_int(first(row, "Is Private", "Private")),
                bool_to_int(first(row, "Is Hidden From Non Members", "Hidden")),
            ),
        )
        names.add(name)
    report["counts"]["raw_spaces"] = len(rows)
    report["counts"]["spaces"] = len(names)
    return names


def import_raw_content(
    conn: sqlite3.Connection,
    kind: str,
    path: Path | None,
    batch_id: str,
) -> int:
    if not path:
        return 0
    _, rows = read_csv_dicts(path)
    table = f"circle_raw_{kind}"
    for row_number, row in enumerate(rows, start=1):
        if kind == "posts":
            conn.execute(
                f"INSERT INTO {table} (import_batch_id, row_number, circle_post_id, circle_member_id, raw_json) VALUES (?, ?, ?, ?, ?)",
                (batch_id, row_number, first(row, "ID", "Post ID", "UID"), first(row, "Member ID", "User ID", "Author ID"), json_dumps(row)),
            )
        elif kind == "comments":
            conn.execute(
                f"INSERT INTO {table} (import_batch_id, row_number, circle_comment_id, circle_post_id, circle_member_id, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
                (batch_id, row_number, first(row, "ID", "Comment ID", "UID"), first(row, "Post ID"), first(row, "Member ID", "User ID", "Author ID"), json_dumps(row)),
            )
        elif kind == "events":
            conn.execute(
                f"INSERT INTO {table} (import_batch_id, row_number, circle_event_id, circle_member_id, raw_json) VALUES (?, ?, ?, ?, ?)",
                (batch_id, row_number, first(row, "ID", "Event ID", "UID"), first(row, "Member ID", "User ID", "Host ID"), json_dumps(row)),
            )
    return len(rows)


def import_members(
    *,
    conn: sqlite3.Connection,
    path: Path,
    batch_id: str,
    namespace: uuid.UUID,
    known_spaces: set[str],
    report: dict[str, Any],
) -> None:
    _, rows = read_csv_dicts(path)
    seen_emails: Counter[str] = Counter()
    skipped_missing_email = 0
    imported_ids: set[str] = set()

    for row_number, row in enumerate(rows, start=1):
        email = normalize_email(first(row, "Email", "Email Address"))
        circle_user_id = first(row, "UID", "User ID", "Member ID", "ID")
        conn.execute(
            """
            INSERT INTO circle_raw_members (
              import_batch_id, row_number, circle_user_id, email, raw_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (batch_id, row_number, circle_user_id, email or None, json_dumps(row)),
        )
        if not email:
            skipped_missing_email += 1
            continue

        seen_emails[email] += 1
        member_id = str(uuid.uuid5(namespace, email))
        imported_ids.add(member_id)
        tags = parse_tags(first(row, "Tags", "Member Tags"))
        spaces = parse_space_access(first(row, "Space Access", "Spaces"), known_spaces)
        lifecycle_status = infer_lifecycle_status(tags)

        first_name = first(row, "First Name", "First name")
        last_name = first(row, "Last Name", "Last name")
        display_name = " ".join(value for value in (first_name, last_name) if value).strip()
        display_name = display_name or first(row, "Name", "Display Name") or email.split("@", 1)[0]
        headline = first_nonempty(row, "Headline__2", "Headline")
        bio = first(row, "Bio", "Biography", "About")
        location = first(row, "Location", "Location Name")
        website = first(row, "Website", "Website URL")
        social_links = compact_json(
            {
                "linkedin": first(row, "LinkedIn URL", "LinkedIn"),
                "twitter": first(row, "Twitter URL", "Twitter", "X URL"),
                "instagram": first(row, "Instagram URL", "Instagram"),
                "facebook": first(row, "Facebook URL", "Facebook"),
            }
        )
        activity = compact_json(
            {
                "posts": int_or_none(first(row, "No. of Posts", "Posts")),
                "comments": int_or_none(first(row, "No. of Comments", "Comments")),
                "likes_received": int_or_none(first(row, "No. of Likes Received", "Likes Received")),
                "activity_score": first(row, "Activity score", "Activity Score"),
                "gamification_points": int_or_none(first(row, "Total Gamification Points")),
            }
        )

        conn.execute(
            """
            INSERT INTO members (
              id, email, first_name, last_name, display_name, avatar_url, headline, bio,
              location_text, website_url, social_links_json, lifecycle_status,
              circle_user_id, circle_profile_url, circle_joined_at, circle_last_active_at,
              circle_active_30d, circle_activity_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
              first_name = excluded.first_name,
              last_name = excluded.last_name,
              display_name = excluded.display_name,
              avatar_url = excluded.avatar_url,
              headline = excluded.headline,
              bio = excluded.bio,
              location_text = excluded.location_text,
              website_url = excluded.website_url,
              social_links_json = excluded.social_links_json,
              lifecycle_status = excluded.lifecycle_status,
              circle_user_id = excluded.circle_user_id,
              circle_profile_url = excluded.circle_profile_url,
              circle_joined_at = excluded.circle_joined_at,
              circle_last_active_at = excluded.circle_last_active_at,
              circle_active_30d = excluded.circle_active_30d,
              circle_activity_json = excluded.circle_activity_json,
              updated_at = datetime('now')
            """,
            (
                member_id,
                email,
                first_name or None,
                last_name or None,
                display_name,
                first(row, "Avatar URL", "Profile Image URL") or None,
                headline or None,
                bio or None,
                location or None,
                website or None,
                json_dumps(social_links),
                lifecycle_status,
                circle_user_id or None,
                first_nonempty(row, "Profile URL__2", "Profile URL") or None,
                parse_datetime(first(row, "Join Date", "Joined At")),
                parse_datetime(first(row, "Last Active", "Last Active At")),
                bool_to_int(first(row, "Active (Signed In Last 30 Days)", "Active")),
                json_dumps(activity),
            ),
        )

        conn.execute(
            """
            INSERT INTO member_import_sources (
              member_id, source, source_user_id, import_batch_id, raw_json
            ) VALUES (?, 'circle', ?, ?, ?)
            ON CONFLICT(member_id, source, import_batch_id) DO UPDATE SET
              source_user_id = excluded.source_user_id,
              raw_json = excluded.raw_json,
              imported_at = datetime('now')
            """,
            (member_id, circle_user_id or None, batch_id, json_dumps(row)),
        )

        conn.execute("DELETE FROM member_tags WHERE member_id = ? AND source = 'circle'", (member_id,))
        for tag in tags:
            conn.execute(
                "INSERT INTO member_tags (member_id, tag, source) VALUES (?, ?, 'circle')",
                (member_id, tag),
            )

        conn.execute("DELETE FROM member_space_access WHERE member_id = ? AND source = 'circle'", (member_id,))
        for space_name in spaces:
            space_id = ensure_space(conn, space_name)
            conn.execute(
                "INSERT INTO member_space_access (member_id, circle_space_id, source) VALUES (?, ?, 'circle')",
                (member_id, space_id),
            )

        prefill = compact_json(
            {
                "preferred_name": first_name or display_name,
                "headline": headline,
                "bio": bio,
                "location_text": location,
                "website_url": website,
                "social_links": social_links,
            }
        )
        conn.execute(
            """
            INSERT INTO member_profiles (
              member_id, preferred_name, headline, bio, location_text, prefill_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(member_id) DO UPDATE SET
              preferred_name = CASE WHEN member_profiles.confirmed_at IS NULL THEN excluded.preferred_name ELSE member_profiles.preferred_name END,
              headline = CASE WHEN member_profiles.confirmed_at IS NULL THEN excluded.headline ELSE member_profiles.headline END,
              bio = CASE WHEN member_profiles.confirmed_at IS NULL THEN excluded.bio ELSE member_profiles.bio END,
              location_text = CASE WHEN member_profiles.confirmed_at IS NULL THEN excluded.location_text ELSE member_profiles.location_text END,
              prefill_json = excluded.prefill_json,
              updated_at = datetime('now')
            """,
            (member_id, first_name or display_name, headline or None, bio or None, location or None, json_dumps(prefill)),
        )

        apply_email_preference(conn, member_id, row)
        apply_provisional_entitlement(conn, member_id, lifecycle_status, namespace)

    report["counts"]["raw_members"] = len(rows)
    report["counts"]["members"] = len(imported_ids)
    report["counts"]["tags"] = conn.execute("SELECT count(*) FROM member_tags").fetchone()[0]
    report["counts"]["space_access"] = conn.execute("SELECT count(*) FROM member_space_access").fetchone()[0]
    report["counts"]["provisional_entitlements"] = conn.execute(
        "SELECT count(*) FROM member_entitlements WHERE source = 'circle_tag'"
    ).fetchone()[0]
    report["warnings"]["missing_email_rows"] = skipped_missing_email
    report["warnings"]["duplicate_normalized_emails"] = sum(
        count - 1 for count in seen_emails.values() if count > 1
    )


def apply_email_preference(conn: sqlite3.Connection, member_id: str, row: dict[str, str]) -> None:
    raw = first(
        row,
        "Email Marketing Preference",
        "Email Preference",
        "Subscribed to Email Marketing",
        "Marketing Email",
    ).lower()
    is_unsubscribed = any(token in raw for token in ("unsubscribed", "opted out", "false", "no"))
    is_subscribed = bool(raw) and not is_unsubscribed and any(
        token in raw for token in ("subscribed", "opted in", "true", "yes")
    )
    conn.execute(
        """
        INSERT INTO member_email_preferences (
          member_id, digest_enabled, pause_all, source
        ) VALUES (?, ?, ?, 'circle')
        ON CONFLICT(member_id) DO UPDATE SET
          digest_enabled = CASE WHEN member_email_preferences.source IN ('circle', 'migration') THEN excluded.digest_enabled ELSE member_email_preferences.digest_enabled END,
          pause_all = CASE WHEN member_email_preferences.source IN ('circle', 'migration') THEN excluded.pause_all ELSE member_email_preferences.pause_all END,
          source = CASE WHEN member_email_preferences.source IN ('circle', 'migration') THEN 'circle' ELSE member_email_preferences.source END,
          updated_at = datetime('now')
        """,
        (member_id, int(is_subscribed), int(is_unsubscribed)),
    )


def apply_provisional_entitlement(
    conn: sqlite3.Connection,
    member_id: str,
    lifecycle_status: str,
    namespace: uuid.UUID,
) -> None:
    entitlement_id = str(uuid.uuid5(namespace, f"entitlement:{member_id}:community:circle"))
    if lifecycle_status == "cancelled":
        conn.execute(
            "DELETE FROM member_entitlements WHERE member_id = ? AND entitlement_key = 'community' AND source = 'circle_tag'",
            (member_id,),
        )
        return
    conn.execute(
        """
        INSERT INTO member_entitlements (
          id, member_id, entitlement_key, source, status, metadata_json
        ) VALUES (?, ?, 'community', 'circle_tag', 'provisional', ?)
        ON CONFLICT(member_id, entitlement_key, source) DO UPDATE SET
          status = 'provisional',
          metadata_json = excluded.metadata_json,
          updated_at = datetime('now')
        """,
        (entitlement_id, member_id, json_dumps({"inferred_lifecycle": lifecycle_status})),
    )


def parse_tags(value: str) -> list[str]:
    value = clean(value)
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return sorted({clean(item) for item in parsed if clean(item)})
    except json.JSONDecodeError:
        pass
    return sorted({part.strip() for part in re.split(r"[,;|\n]", value) if part.strip()})


def parse_space_access(value: str, known_spaces: set[str]) -> list[str]:
    value = clean(value)
    if not value:
        return []
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return list(dict.fromkeys(clean(item) for item in parsed if clean(item)))
        except json.JSONDecodeError:
            pass

    matches: list[tuple[int, int, str]] = []
    occupied: list[tuple[int, int]] = []
    covered = [False] * len(value)
    for name in sorted(known_spaces, key=len, reverse=True):
        for match in re.finditer(re.escape(name), value, flags=re.IGNORECASE):
            span = match.span()
            if any(max(span[0], old[0]) < min(span[1], old[1]) for old in occupied):
                continue
            occupied.append(span)
            matches.append((span[0], span[1], name))
            for index in range(span[0], span[1]):
                covered[index] = True
    if not matches:
        return [part.strip() for part in re.split(r"[,;|\n]", value) if part.strip()]

    parsed = [name for _, _, name in sorted(matches)]
    leftover = "".join(" " if covered[index] else char for index, char in enumerate(value))
    parsed.extend(part.strip(" ,;|") for part in re.split(r"[,;|\n]", leftover) if part.strip(" ,;|"))
    return list(dict.fromkeys(parsed))


def ensure_space(conn: sqlite3.Connection, name: str) -> str:
    row = conn.execute("SELECT circle_space_id FROM circle_spaces WHERE name = ?", (name,)).fetchone()
    if row:
        return str(row[0])
    space_id = f"derived:{slugify(name)}"
    conn.execute(
        "INSERT OR IGNORE INTO circle_spaces (circle_space_id, name, slug, source) VALUES (?, ?, ?, 'member_space_access')",
        (space_id, name, slugify(name)),
    )
    return space_id


def infer_lifecycle_status(tags: list[str]) -> str:
    normalized = " | ".join(tags).lower()
    if "cancelled" in normalized or "canceled" in normalized:
        return "cancelled"
    if "lifetime" in normalized:
        return "lifetime"
    if "gift" in normalized:
        return "gifted"
    if tags:
        return "active"
    return "unknown"


def first(row: dict[str, str], *names: str) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for name in names:
        value = row.get(name)
        if clean(value):
            return clean(value)
        value = lowered.get(name.lower())
        if clean(value):
            return clean(value)
    return ""


def first_nonempty(row: dict[str, str], *names: str) -> str:
    return first(row, *names)


def normalize_email(value: str) -> str:
    value = clean(value).lower()
    return value if "@" in value and not any(char.isspace() for char in value) else ""


def parse_datetime(value: str) -> str | None:
    value = clean(value)
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return value


def bool_to_int(value: Any) -> int:
    return int(clean(value).lower() in {"1", "yes", "true", "y", "active", "subscribed"})


def int_or_none(value: Any) -> int | None:
    value = clean(value).replace(",", "")
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def compact_json(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item not in (None, "", {}, [])}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def clean(value: Any) -> str:
    return str(value or "").strip()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
