import json
import markdown

from pathlib import Path

CONTENT_DIR = Path(__file__).parent / 'content'


def load_about():
    with open(CONTENT_DIR / "about.md", 'r') as f:
        return markdown.markdown(f.read())


def load_projects():
    with open(CONTENT_DIR / "projects.json", 'r') as f:
        return json.load(f)


def load_skills():
    with open(CONTENT_DIR / "skills.json", 'r') as f:
        return json.load(f)


def load_contact():
    with open(CONTENT_DIR / "contact.json", 'r') as f:
        return json.load(f)