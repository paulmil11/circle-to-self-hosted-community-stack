#!/usr/bin/env python3
"""Audit a Circle migration database without printing member PII."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Imported SQLite database.")
    parser.add_argument("--json", help="Optional JSON output path.")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.is_file():
        raise SystemExit(f"Database not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        report = build_report(conn)
    finally:
        conn.close()

    print(f"Database: {db_path}")
    for section, values in report.items():
        print(f"\n{section}:")
        for key, value in values.items():
            print(f"  {key}: {value}")

    if args.json:
        output = Path(args.json).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failures = report["integrity"]
    if any(value for key, value in failures.items() if key != "foreign_key_violations"):
        raise SystemExit(2)
    if failures["foreign_key_violations"]:
        raise SystemExit(2)


def build_report(conn: sqlite3.Connection) -> dict[str, Any]:
    raw_members = scalar(conn, "SELECT count(*) FROM circle_raw_members")
    normalized_members = scalar(conn, "SELECT count(*) FROM members")
    missing_email = scalar(
        conn,
        "SELECT count(*) FROM circle_raw_members WHERE email IS NULL OR trim(email) = ''",
    )
    duplicate_email_rows = scalar(
        conn,
        """
        SELECT coalesce(sum(row_count - 1), 0)
        FROM (
          SELECT lower(trim(email)) AS normalized_email, count(*) AS row_count
          FROM circle_raw_members
          WHERE email IS NOT NULL AND trim(email) != ''
          GROUP BY lower(trim(email))
          HAVING count(*) > 1
        )
        """,
    )
    lifecycle = {
        row["lifecycle_status"]: row["count"]
        for row in conn.execute(
            "SELECT lifecycle_status, count(*) AS count FROM members GROUP BY lifecycle_status ORDER BY lifecycle_status"
        )
    }
    source_member_gap = scalar(
        conn,
        """
        SELECT count(*)
        FROM members m
        LEFT JOIN member_import_sources s ON s.member_id = m.id AND s.source = 'circle'
        WHERE s.member_id IS NULL
        """,
    )
    profile_gap = scalar(
        conn,
        """
        SELECT count(*)
        FROM members m
        LEFT JOIN member_profiles p ON p.member_id = m.id
        WHERE p.member_id IS NULL
        """,
    )
    foreign_key_violations = len(list(conn.execute("PRAGMA foreign_key_check")))

    return {
        "counts": {
            "import_batches": scalar(conn, "SELECT count(*) FROM circle_import_batches"),
            "raw_members": raw_members,
            "normalized_members": normalized_members,
            "raw_spaces": scalar(conn, "SELECT count(*) FROM circle_raw_spaces"),
            "normalized_spaces": scalar(conn, "SELECT count(*) FROM circle_spaces"),
            "raw_posts": scalar(conn, "SELECT count(*) FROM circle_raw_posts"),
            "raw_comments": scalar(conn, "SELECT count(*) FROM circle_raw_comments"),
            "raw_events": scalar(conn, "SELECT count(*) FROM circle_raw_events"),
            "tags": scalar(conn, "SELECT count(*) FROM member_tags"),
            "space_access": scalar(conn, "SELECT count(*) FROM member_space_access"),
            "profiles": scalar(conn, "SELECT count(*) FROM member_profiles"),
            "email_preferences": scalar(conn, "SELECT count(*) FROM member_email_preferences"),
            "provisional_entitlements": scalar(
                conn,
                "SELECT count(*) FROM member_entitlements WHERE status = 'provisional'",
            ),
        },
        "lifecycle": lifecycle,
        "review": {
            "missing_email_rows": missing_email,
            "duplicate_normalized_email_rows": duplicate_email_rows,
            "circle_hosted_avatar_urls": scalar(
                conn,
                "SELECT count(*) FROM members WHERE lower(avatar_url) LIKE '%circle%'",
            ),
            "unsubscribed_or_paused": scalar(
                conn,
                "SELECT count(*) FROM member_email_preferences WHERE pause_all = 1",
            ),
            "unconfirmed_profiles": scalar(
                conn,
                "SELECT count(*) FROM member_profiles WHERE confirmed_at IS NULL",
            ),
        },
        "integrity": {
            "foreign_key_violations": foreign_key_violations,
            "members_without_circle_source": source_member_gap,
            "members_without_profile": profile_gap,
            "normalized_member_overflow": max(0, normalized_members - (raw_members - missing_email)),
        },
    }


def scalar(conn: sqlite3.Connection, sql: str) -> int:
    value = conn.execute(sql).fetchone()[0]
    return int(value or 0)


if __name__ == "__main__":
    main()
