"""Read and write functions for the content tables.

About, contact and impressum live in the key-value ``site_setting`` table,
contact and impressum as JSON blobs. Projects live in ``project`` with the
tech stack stored as JSON text. Skills live in ``skill_category`` and
``skill``. Every query is parameterised, no SQL is built from input.
"""

import json

from app.content.schemas import (
    ContactContent,
    ImpressumContent,
    ProjectWrite,
    SkillCategoryWrite,
    SkillWrite,
)
from app.db.connection import get_connection, now

ABOUT_KEY = "about_text"
CONTACT_KEY = "contact"
IMPRESSUM_KEY = "impressum"


# --- site_setting helpers ------------------------------------------------


def _get_setting(conn, key: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM site_setting WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row is not None else None


def _set_setting(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO site_setting (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT (key) DO UPDATE SET "
        "value = excluded.value, updated_at = excluded.updated_at",
        (key, value, now()),
    )


def _delete_setting(conn, key: str) -> bool:
    cursor = conn.execute("DELETE FROM site_setting WHERE key = ?", (key,))
    return cursor.rowcount > 0


# --- about ---------------------------------------------------------------


def get_about() -> str | None:
    with get_connection() as conn:
        return _get_setting(conn, ABOUT_KEY)


def set_about(text: str) -> None:
    with get_connection() as conn:
        _set_setting(conn, ABOUT_KEY, text)
        conn.commit()


def delete_about() -> bool:
    with get_connection() as conn:
        deleted = _delete_setting(conn, ABOUT_KEY)
        conn.commit()
    return deleted


# --- contact and impressum (JSON blobs) ----------------------------------


def get_contact() -> dict | None:
    with get_connection() as conn:
        raw = _get_setting(conn, CONTACT_KEY)
    return json.loads(raw) if raw is not None else None


def set_contact(data: ContactContent) -> None:
    with get_connection() as conn:
        _set_setting(
            conn, CONTACT_KEY, json.dumps(data.model_dump(), ensure_ascii=False)
        )
        conn.commit()


def delete_contact() -> bool:
    with get_connection() as conn:
        deleted = _delete_setting(conn, CONTACT_KEY)
        conn.commit()
    return deleted


def get_impressum() -> dict | None:
    with get_connection() as conn:
        raw = _get_setting(conn, IMPRESSUM_KEY)
    return json.loads(raw) if raw is not None else None


def set_impressum(data: ImpressumContent) -> None:
    with get_connection() as conn:
        _set_setting(
            conn, IMPRESSUM_KEY, json.dumps(data.model_dump(), ensure_ascii=False)
        )
        conn.commit()


def delete_impressum() -> bool:
    with get_connection() as conn:
        deleted = _delete_setting(conn, IMPRESSUM_KEY)
        conn.commit()
    return deleted


# --- projects ------------------------------------------------------------


def _project_row_to_dict(row) -> dict:
    data = dict(row)
    data["tech_stack"] = json.loads(data["tech_stack"]) if data["tech_stack"] else []
    data["visible"] = bool(data["visible"])
    return data


def list_projects(include_hidden: bool = True) -> list[dict]:
    query = (
        "SELECT id, name, tagline, problem, solution, learning, tech_stack, "
        "demo_link, github_link, status, sort_order, visible FROM project"
    )
    if not include_hidden:
        query += " WHERE visible = 1"
    query += " ORDER BY sort_order, id"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [_project_row_to_dict(row) for row in rows]


def get_project(project_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, tagline, problem, solution, learning, tech_stack, "
            "demo_link, github_link, status, sort_order, visible "
            "FROM project WHERE id = ?",
            (project_id,),
        ).fetchone()
    return _project_row_to_dict(row) if row is not None else None


def _project_params(data: ProjectWrite) -> tuple:
    return (
        data.name,
        data.tagline,
        data.problem,
        data.solution,
        data.learning,
        json.dumps(data.tech_stack, ensure_ascii=False),
        data.demo_link,
        data.github_link,
        data.status,
        data.sort_order,
        1 if data.visible else 0,
    )


def create_project(data: ProjectWrite) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO project "
            "(name, tagline, problem, solution, learning, tech_stack, "
            "demo_link, github_link, status, sort_order, visible) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            _project_params(data),
        )
        conn.commit()
        project_id = cursor.lastrowid
    return get_project(project_id)  # type: ignore[return-value]


def update_project(project_id: int, data: ProjectWrite) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE project SET "
            "name = ?, tagline = ?, problem = ?, solution = ?, learning = ?, "
            "tech_stack = ?, demo_link = ?, github_link = ?, status = ?, "
            "sort_order = ?, visible = ? WHERE id = ?",
            (*_project_params(data), project_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_project(project_id)


def delete_project(project_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM project WHERE id = ?", (project_id,))
        conn.commit()
    return cursor.rowcount > 0


# --- skills --------------------------------------------------------------


def list_skill_categories() -> list[dict]:
    with get_connection() as conn:
        categories = conn.execute(
            "SELECT id, name, sort_order FROM skill_category "
            "ORDER BY sort_order, id"
        ).fetchall()
        skills = conn.execute(
            "SELECT id, category_id, name, sort_order FROM skill "
            "ORDER BY sort_order, id"
        ).fetchall()
    by_category: dict[int, list[dict]] = {}
    for skill in skills:
        by_category.setdefault(skill["category_id"], []).append(
            {"id": skill["id"], "name": skill["name"], "sort_order": skill["sort_order"]}
        )
    return [
        {
            "id": category["id"],
            "name": category["name"],
            "sort_order": category["sort_order"],
            "skills": by_category.get(category["id"], []),
        }
        for category in categories
    ]


def _get_category(conn, category_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, name, sort_order FROM skill_category WHERE id = ?",
        (category_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def create_category(data: SkillCategoryWrite) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO skill_category (name, sort_order) VALUES (?, ?)",
            (data.name, data.sort_order),
        )
        conn.commit()
        category_id = cursor.lastrowid
        category = _get_category(conn, category_id)
    return {**category, "skills": []}  # type: ignore[dict-item]


def update_category(category_id: int, data: SkillCategoryWrite) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE skill_category SET name = ?, sort_order = ? WHERE id = ?",
            (data.name, data.sort_order, category_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        category = _get_category(conn, category_id)
        skills = conn.execute(
            "SELECT id, name, sort_order FROM skill WHERE category_id = ? "
            "ORDER BY sort_order, id",
            (category_id,),
        ).fetchall()
    return {**category, "skills": [dict(s) for s in skills]}  # type: ignore[dict-item]


def delete_category(category_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM skill WHERE category_id = ?", (category_id,))
        cursor = conn.execute(
            "DELETE FROM skill_category WHERE id = ?", (category_id,)
        )
        conn.commit()
    return cursor.rowcount > 0


def create_skill(category_id: int, data: SkillWrite) -> dict | None:
    with get_connection() as conn:
        if _get_category(conn, category_id) is None:
            return None
        cursor = conn.execute(
            "INSERT INTO skill (category_id, name, sort_order) VALUES (?, ?, ?)",
            (category_id, data.name, data.sort_order),
        )
        conn.commit()
        skill_id = cursor.lastrowid
        row = conn.execute(
            "SELECT id, name, sort_order FROM skill WHERE id = ?", (skill_id,)
        ).fetchone()
    return dict(row)


def update_skill(skill_id: int, data: SkillWrite) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE skill SET name = ?, sort_order = ? WHERE id = ?",
            (data.name, data.sort_order, skill_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        row = conn.execute(
            "SELECT id, name, sort_order FROM skill WHERE id = ?", (skill_id,)
        ).fetchone()
    return dict(row)


def delete_skill(skill_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM skill WHERE id = ?", (skill_id,))
        conn.commit()
    return cursor.rowcount > 0
