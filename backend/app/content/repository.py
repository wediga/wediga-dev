"""Read and write functions for the content tables.

About, contact and impressum live in the key-value ``site_setting`` table as
``jsonb`` (the about text as a JSON string, contact and impressum as objects).
Projects live in ``project`` with the tech stack as a ``jsonb`` list, skills in
``skill_category`` and ``skill``. Every
query goes through SQLAlchemy with bound parameters, no SQL is built from
input.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.content.models import Project, SiteSetting, Skill, SkillCategory
from app.content.schemas import (
    ContactContent,
    ImpressumContent,
    ProjectWrite,
    SkillCategoryWrite,
    SkillWrite,
)
from app.db.connection import get_session, now

ABOUT_KEY = "about_text"
CONTACT_KEY = "contact"
IMPRESSUM_KEY = "impressum"


# --- site_setting helpers ------------------------------------------------


def _find_setting(session: Session, key: str) -> SiteSetting | None:
    return session.scalar(select(SiteSetting).where(SiteSetting.key == key))


def _get_setting(session: Session, key: str) -> str | dict | None:
    setting = _find_setting(session, key)
    return setting.value if setting is not None else None


def set_setting(session: Session, key: str, value: str | dict) -> None:
    statement = insert(SiteSetting).values(key=key, value=value, updated_at=now())
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[SiteSetting.key],
            set_={
                "value": statement.excluded.value,
                "updated_at": statement.excluded.updated_at,
            },
        )
    )


def _delete_setting(session: Session, key: str) -> bool:
    setting = _find_setting(session, key)

    if setting is None:
        return False

    session.delete(setting)

    return True


# --- about ---------------------------------------------------------------


def get_about() -> str | None:
    with get_session() as session:
        text = _get_setting(session, ABOUT_KEY)

    assert text is None or isinstance(text, str)

    return text


def set_about(text: str) -> None:
    with get_session() as session:
        set_setting(session, ABOUT_KEY, text)
        session.commit()


def delete_about() -> bool:
    with get_session() as session:
        deleted = _delete_setting(session, ABOUT_KEY)
        session.commit()

    return deleted


# --- contact and impressum (JSON objects) --------------------------------


def _get_object(key: str) -> dict | None:
    with get_session() as session:
        data = _get_setting(session, key)

    assert data is None or isinstance(data, dict)

    return data


def get_contact() -> dict | None:
    return _get_object(CONTACT_KEY)


def set_contact(data: ContactContent) -> None:
    with get_session() as session:
        set_setting(session, CONTACT_KEY, data.model_dump())
        session.commit()


def delete_contact() -> bool:
    with get_session() as session:
        deleted = _delete_setting(session, CONTACT_KEY)
        session.commit()

    return deleted


def get_impressum() -> dict | None:
    return _get_object(IMPRESSUM_KEY)


def set_impressum(data: ImpressumContent) -> None:
    with get_session() as session:
        set_setting(session, IMPRESSUM_KEY, data.model_dump())
        session.commit()


def delete_impressum() -> bool:
    with get_session() as session:
        deleted = _delete_setting(session, IMPRESSUM_KEY)
        session.commit()

    return deleted


# --- projects ------------------------------------------------------------


def _project_to_dict(project: Project) -> dict:
    return {**project.as_dict(), "tech_stack": project.tech_stack or []}


def list_projects(include_hidden: bool = True) -> list[dict]:
    query = select(Project)

    if not include_hidden:
        query = query.where(Project.visible)
    query = query.order_by(Project.sort_order, Project.id)

    with get_session() as session:
        return [_project_to_dict(project) for project in session.scalars(query)]


def get_project(project_id: uuid.UUID) -> dict | None:
    with get_session() as session:
        project = session.get(Project, project_id)
        return _project_to_dict(project) if project is not None else None


def create_project(data: ProjectWrite) -> dict:
    with get_session() as session:
        project = Project(**data.model_dump())
        session.add(project)
        session.commit()

        return _project_to_dict(project)


def update_project(project_id: uuid.UUID, data: ProjectWrite) -> dict | None:
    with get_session() as session:
        project = session.get(Project, project_id)

        if project is None:
            return None

        for key, value in data.model_dump().items():
            setattr(project, key, value)
        session.commit()

        return _project_to_dict(project)


def delete_project(project_id: uuid.UUID) -> bool:
    with get_session() as session:
        project = session.get(Project, project_id)

        if project is None:
            return False

        session.delete(project)
        session.commit()

    return True


# --- skills --------------------------------------------------------------


def _skill_to_dict(skill: Skill) -> dict:
    return {"id": skill.id, "name": skill.name, "sort_order": skill.sort_order}


def list_skill_categories() -> list[dict]:
    with get_session() as session:
        categories = session.scalars(
            select(SkillCategory).order_by(SkillCategory.sort_order, SkillCategory.id)
        ).all()
        skills = session.scalars(select(Skill).order_by(Skill.sort_order, Skill.id))
        by_category: dict[uuid.UUID, list[dict]] = {}

        for skill in skills:
            by_category.setdefault(skill.category_id, []).append(_skill_to_dict(skill))

        return [
            {**category.as_dict(), "skills": by_category.get(category.id, [])}
            for category in categories
        ]


def create_category(data: SkillCategoryWrite) -> dict:
    with get_session() as session:
        category = SkillCategory(name=data.name, sort_order=data.sort_order)
        session.add(category)
        session.commit()

        return {**category.as_dict(), "skills": []}


def update_category(category_id: uuid.UUID, data: SkillCategoryWrite) -> dict | None:
    with get_session() as session:
        category = session.get(SkillCategory, category_id)

        if category is None:
            return None

        category.name = data.name
        category.sort_order = data.sort_order
        session.commit()
        skills = session.scalars(
            select(Skill)
            .where(Skill.category_id == category_id)
            .order_by(Skill.sort_order, Skill.id)
        )

        return {
            **category.as_dict(),
            "skills": [_skill_to_dict(skill) for skill in skills],
        }


def delete_category(category_id: uuid.UUID) -> bool:
    with get_session() as session:
        category = session.get(SkillCategory, category_id)

        if category is None:
            return False

        session.execute(delete(Skill).where(Skill.category_id == category_id))
        session.delete(category)
        session.commit()

    return True


def create_skill(category_id: uuid.UUID, data: SkillWrite) -> dict | None:
    with get_session() as session:
        if session.get(SkillCategory, category_id) is None:
            return None

        skill = Skill(
            category_id=category_id, name=data.name, sort_order=data.sort_order
        )
        session.add(skill)
        session.commit()

        return _skill_to_dict(skill)


def update_skill(skill_id: uuid.UUID, data: SkillWrite) -> dict | None:
    with get_session() as session:
        skill = session.get(Skill, skill_id)

        if skill is None:
            return None

        skill.name = data.name
        skill.sort_order = data.sort_order
        session.commit()

        return _skill_to_dict(skill)


def delete_skill(skill_id: uuid.UUID) -> bool:
    with get_session() as session:
        skill = session.get(Skill, skill_id)

        if skill is None:
            return False

        session.delete(skill)
        session.commit()

    return True
