"""Idempotent seed of database content from the content directory.

Reads the content files and upserts them on a stable natural key, so a re-run
makes no duplicates and pulls in file edits, never writing back to the files.
The admin-managed ``visible`` flag on a project survives a re-seed, so it never
re-shows a project the admin hid. The summary counts entries processed, not
rows changed.
"""

import json
from pathlib import Path

from app.content import repository
from app.db.connection import get_connection
from app.paths import content_dir


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"content file missing: {path}")
    return path


def _seed_about(conn, base: Path) -> int:
    path = _require(base / "about.md")
    text = path.read_text(encoding="utf-8")
    repository._set_setting(conn, "about_text", text)
    return 1


def _seed_setting_json(conn, base: Path, filename: str, key: str) -> int:
    path = _require(base / filename)
    data = json.loads(path.read_text(encoding="utf-8"))
    repository._set_setting(conn, key, json.dumps(data, ensure_ascii=False))
    return 1


def _seed_projects(conn, base: Path) -> int:
    path = _require(base / "projects.json")
    projects = json.loads(path.read_text(encoding="utf-8"))
    for index, item in enumerate(projects):
        links = item.get("links", {}) or {}
        conn.execute(
            "INSERT INTO project "
            "(name, tagline, problem, solution, learning, tech_stack, "
            "demo_link, github_link, status, sort_order, visible) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1) "
            "ON CONFLICT (name) DO UPDATE SET "
            "tagline = excluded.tagline, problem = excluded.problem, "
            "solution = excluded.solution, learning = excluded.learning, "
            "tech_stack = excluded.tech_stack, demo_link = excluded.demo_link, "
            "github_link = excluded.github_link, status = excluded.status, "
            "sort_order = excluded.sort_order",
            (
                item.get("name"),
                item.get("tagline"),
                item.get("problem"),
                item.get("solution"),
                item.get("learning"),
                json.dumps(item.get("tech_stack", []), ensure_ascii=False),
                links.get("demo"),
                links.get("github"),
                item.get("status"),
                index,
            ),
        )
    return len(projects)


def _seed_skills(conn, base: Path) -> tuple[int, int]:
    path = _require(base / "skills.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    category_count = 0
    skill_count = 0
    for cat_index, (category, names) in enumerate(data.items()):
        conn.execute(
            "INSERT INTO skill_category (name, sort_order) VALUES (?, ?) "
            "ON CONFLICT (name) DO UPDATE SET sort_order = excluded.sort_order",
            (category, cat_index),
        )
        category_count += 1
        row = conn.execute(
            "SELECT id FROM skill_category WHERE name = ?", (category,)
        ).fetchone()
        category_id = row[0]
        for skill_index, name in enumerate(names):
            conn.execute(
                "INSERT INTO skill (category_id, name, sort_order) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT (category_id, name) DO UPDATE SET "
                "sort_order = excluded.sort_order",
                (category_id, name, skill_index),
            )
            skill_count += 1
    return category_count, skill_count


def run_seed() -> dict[str, int]:
    """Read content files into the database and return processed-entry counts."""
    base = content_dir()
    summary: dict[str, int] = {}
    with get_connection() as conn:
        try:
            summary["about"] = _seed_about(conn, base)
            summary["contact"] = _seed_setting_json(
                conn, base, "contact.json", "contact"
            )
            summary["impressum"] = _seed_setting_json(
                conn, base, "impressum.json", "impressum"
            )
            summary["projects"] = _seed_projects(conn, base)
            categories, skills = _seed_skills(conn, base)
            summary["skill_categories"] = categories
            summary["skills"] = skills
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return summary


def main() -> None:
    summary = run_seed()
    for key, value in summary.items():
        print(f"{key}: {value} processed")


if __name__ == "__main__":
    main()
