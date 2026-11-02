"""Read and write functions for the content tables.

The profile is a single row with its links and its postal address, projects
live in ``project`` with the tech stack as a ``jsonb`` list, skills in
``skill_category`` and ``skill``. Every query goes through SQLAlchemy with
bound parameters, no SQL is built from input.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.content.models import (
    LinkKind,
    PostalAddress,
    Profile,
    ProfileLink,
    Project,
    Skill,
    SkillCategory,
)
from app.content.schemas import (
    ProfileAddress,
    ProfileContent,
    ProjectWrite,
    SkillCategoryWrite,
    SkillWrite,
)
from app.db.connection import get_session

# --- profile -------------------------------------------------------------


def get_profile() -> ProfileContent | None:
    with get_session() as session:
        profile = session.scalar(select(Profile))

        if profile is None:
            return None

        links = session.execute(
            select(LinkKind.key, ProfileLink.url)
            .join(LinkKind, LinkKind.id == ProfileLink.link_kind_id)
            .where(ProfileLink.profile_id == profile.id)
        )
        address = session.scalar(
            select(PostalAddress).where(PostalAddress.profile_id == profile.id)
        )

        return ProfileContent.model_validate(
            {
                "name": profile.name,
                "email": profile.email,
                "about_md": profile.about_md,
                "links": dict(links.all()),
                "address": ProfileAddress.model_validate(address, from_attributes=True)
                if address is not None
                else None,
            }
        )


def save_profile(session: Session, data: ProfileContent) -> None:
    """Write the single profile row and replace its links and address."""
    profile = session.scalar(select(Profile))

    if profile is None:
        profile = Profile(name=data.name, email=data.email, about_md=data.about_md)
        session.add(profile)
        session.flush()
    else:
        profile.name = data.name
        profile.email = data.email
        profile.about_md = data.about_md

    session.execute(delete(ProfileLink).where(ProfileLink.profile_id == profile.id))
    session.execute(delete(PostalAddress).where(PostalAddress.profile_id == profile.id))

    if data.links:
        session.execute(
            insert(LinkKind)
            .values([{"key": kind} for kind in data.links])
            .on_conflict_do_nothing()
        )
        kind_ids = dict(
            session.execute(
                select(LinkKind.key, LinkKind.id).where(LinkKind.key.in_(data.links))
            ).all()
        )
        session.add_all(
            ProfileLink(profile_id=profile.id, link_kind_id=kind_ids[kind], url=url)
            for kind, url in data.links.items()
        )

    if data.address is not None:
        session.add(PostalAddress(profile_id=profile.id, **data.address.model_dump()))


def set_profile(data: ProfileContent) -> None:
    with get_session() as session:
        save_profile(session, data)
        session.commit()


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
