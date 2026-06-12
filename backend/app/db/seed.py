"""Idempotent seed of database content from the content directory.

The seed reads ``about.md``, ``contact.json``, ``impressum.json``,
``projects.json`` and ``skills.json`` and writes them into the database
without ever modifying the files. Each row has a stable natural key and is
written with ``INSERT ... ON CONFLICT ... DO UPDATE`` (upsert), so a second
run produces no duplicates and pulls in content edits made in the files. The
admin-managed ``visible`` flag on a project is left untouched on update, so a
re-seed never re-shows a project the admin hid. The returned summary counts
the rows actually written or updated via ``cursor.rowcount``.
"""

import json
from pathlib import Path

from app.db.connection import get_connection, now
from app.paths import content_dir


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"content file missing: {path}")
    return path


def _upsert_setting(conn, key: str, value: str) -> int:
    cursor = conn.execute(
        "INSERT INTO site_setting (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT (key) DO UPDATE SET "
        "value = excluded.value, updated_at = excluded.updated_at "
        "WHERE site_setting.value <> excluded.value",
        (key, value, now()),
    )
    return cursor.rowcount


def _seed_about(conn, base: Path) -> int:
    path = _require(base / "about.md")
    text = path.read_text(encoding="utf-8")
    return _upsert_setting(conn, "about_text", text)


def _seed_setting_json(conn, base: Path, filename: str, key: str) -> int:
    path = _require(base / filename)
    data = json.loads(path.read_text(encoding="utf-8"))
    return _upsert_setting(conn, key, json.dumps(data, ensure_ascii=False))


def _seed_projects(conn, base: Path) -> int:
    path = _require(base / "projects.json")
    projects = json.loads(path.read_text(encoding="utf-8"))
    written = 0
    for index, item in enumerate(projects):
        links = item.get("links", {}) or {}
        cursor = conn.execute(
            "INSERT INTO project "
            "(name, tagline, problem, solution, learning, tech_stack, "
            "demo_link, github_link, status, sort_order, visible) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1) "
            "ON CONFLICT (name) DO UPDATE SET "
            "tagline = excluded.tagline, problem = excluded.problem, "
            "solution = excluded.solution, learning = excluded.learning, "
            "tech_stack = excluded.tech_stack, demo_link = excluded.demo_link, "
            "github_link = excluded.github_link, status = excluded.status, "
            "sort_order = excluded.sort_order "
            "WHERE project.tagline IS NOT excluded.tagline "
            "OR project.problem IS NOT excluded.problem "
            "OR project.solution IS NOT excluded.solution "
            "OR project.learning IS NOT excluded.learning "
            "OR project.tech_stack IS NOT excluded.tech_stack "
            "OR project.demo_link IS NOT excluded.demo_link "
            "OR project.github_link IS NOT excluded.github_link "
            "OR project.status IS NOT excluded.status "
            "OR project.sort_order IS NOT excluded.sort_order",
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
        written += cursor.rowcount
    return written


def _seed_skills(conn, base: Path) -> tuple[int, int]:
    path = _require(base / "skills.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    category_count = 0
    skill_count = 0
    for cat_index, (category, names) in enumerate(data.items()):
        cursor = conn.execute(
            "INSERT INTO skill_category (name, sort_order) VALUES (?, ?) "
            "ON CONFLICT (name) DO UPDATE SET sort_order = excluded.sort_order "
            "WHERE skill_category.sort_order IS NOT excluded.sort_order",
            (category, cat_index),
        )
        category_count += cursor.rowcount
        row = conn.execute(
            "SELECT id FROM skill_category WHERE name = ?", (category,)
        ).fetchone()
        category_id = row[0]
        for skill_index, name in enumerate(names):
            cursor = conn.execute(
                "INSERT INTO skill (category_id, name, sort_order) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT (category_id, name) DO UPDATE SET "
                "sort_order = excluded.sort_order "
                "WHERE skill.sort_order IS NOT excluded.sort_order",
                (category_id, name, skill_index),
            )
            skill_count += cursor.rowcount
    return category_count, skill_count


def run_seed() -> dict[str, int]:
    """Read content files into the database and return written-row counts."""
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
        print(f"{key}: {value} written")


if __name__ == "__main__":
    main()
