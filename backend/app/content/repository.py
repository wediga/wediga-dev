"""Read and write functions for the content tables.

The profile is a single row with its links and its postal address, and a
skill is a ``technology`` placed in a ``skill_category``. Every query goes
through SQLAlchemy with bound parameters, no SQL is built from input.
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.content.models import (
    LinkKind,
    PostalAddress,
    Profile,
    ProfileLink,
    Skill,
    SkillCategory,
    Technology,
)
from app.content.schemas import (
    ProfileAddress,
    ProfileContent,
    SkillCategoryWrite,
    TechnologyWrite,
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


# --- skills and technologies ---------------------------------------------


def _skills_by_category(session: Session, *conditions) -> dict[uuid.UUID, list[dict]]:
    rows = session.execute(
        select(Skill.skill_category_id, Skill.id, Technology.name, Skill.sort_order)
        .join(Technology, Technology.id == Skill.technology_id)
        .where(*conditions)
        .order_by(Skill.sort_order, Technology.name)
    )
    by_category: dict[uuid.UUID, list[dict]] = {}

    for row in rows:
        by_category.setdefault(row.skill_category_id, []).append(
            {"id": row.id, "name": row.name, "sort_order": row.sort_order}
        )

    return by_category


def list_skill_categories() -> list[dict]:
    with get_session() as session:
        categories = session.scalars(
            select(SkillCategory).order_by(SkillCategory.sort_order, SkillCategory.id)
        ).all()
        by_category = _skills_by_category(session)

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
        by_category = _skills_by_category(
            session, Skill.skill_category_id == category_id
        )

        return {**category.as_dict(), "skills": by_category.get(category_id, [])}


def delete_category(category_id: uuid.UUID) -> bool:
    """Delete a category and its skills. The technologies stay, without one."""
    with get_session() as session:
        category = session.get(SkillCategory, category_id)

        if category is None:
            return False

        session.execute(delete(Skill).where(Skill.skill_category_id == category_id))
        session.delete(category)
        session.commit()

    return True


def _technology_to_dict(technology: Technology, skill: Skill | None) -> dict:
    return {
        **technology.as_dict(),
        "skill_category_id": skill.skill_category_id if skill else None,
        "sort_order": skill.sort_order if skill else None,
    }


def _place(
    session: Session, technology_id: uuid.UUID, category_id: uuid.UUID | None
) -> Skill | None:
    """Put a technology into a category, at its end when it moves there, or
    take it out of its category when there is none."""
    skill = session.scalar(select(Skill).where(Skill.technology_id == technology_id))

    if category_id is None:
        if skill is not None:
            session.delete(skill)

        return None

    if skill is not None and skill.skill_category_id == category_id:
        return skill

    last = session.scalar(
        select(func.max(Skill.sort_order)).where(Skill.skill_category_id == category_id)
    )
    sort_order = 0 if last is None else last + 1

    if skill is None:
        skill = Skill(
            skill_category_id=category_id,
            technology_id=technology_id,
            sort_order=sort_order,
        )
        session.add(skill)
    else:
        skill.skill_category_id = category_id
        skill.sort_order = sort_order

    return skill


def list_technologies() -> list[dict]:
    with get_session() as session:
        rows = session.execute(
            select(Technology, Skill)
            .outerjoin(Skill, Skill.technology_id == Technology.id)
            # In the order of their category, technologies without one last.
            .order_by(Skill.sort_order, Technology.name)
        )

        return [_technology_to_dict(technology, skill) for technology, skill in rows]


def create_technology(data: TechnologyWrite) -> dict:
    with get_session() as session:
        technology = Technology(topic=data.topic, name=data.name)
        session.add(technology)
        session.flush()
        skill = _place(session, technology.id, data.skill_category_id)
        session.commit()

        return _technology_to_dict(technology, skill)


def update_technology(technology_id: uuid.UUID, data: TechnologyWrite) -> dict | None:
    with get_session() as session:
        technology = session.get(Technology, technology_id)

        if technology is None:
            return None

        technology.topic = data.topic
        technology.name = data.name
        skill = _place(session, technology_id, data.skill_category_id)
        session.commit()

        return _technology_to_dict(technology, skill)


def delete_technology(technology_id: uuid.UUID) -> bool:
    """Delete a technology, and with it its skill."""
    with get_session() as session:
        technology = session.get(Technology, technology_id)

        if technology is None:
            return False

        session.delete(technology)
        session.commit()

    return True
