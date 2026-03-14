import os
import starlette.middleware.sessions as sessions

from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

from content_loader import load_about, load_projects, load_skills, load_contact

app = FastAPI()

app.add_middleware(sessions.SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET"))

templates = Jinja2Templates(directory="templates")

users = {
    os.environ.get("RECRUITER_USERNAME"): {"password": os.environ.get("RECRUITER_PASSWORD"), "role": "recruiter"},
    os.environ.get("FRIENDS_USERNAME"): {"password": os.environ.get("FRIENDS_PASSWORD"), "role": "friends"},
}
role_redirects = {
      "recruiter": "/portfolio",
      "friends": "/friends",
  }


@app.get("/")
def landing_page(request: Request):
    return templates.TemplateResponse("landing_page.html", {"request": request})

@app.get("/login")
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_post(request: Request, username: str = Form(), password: str = Form()):

    if username in users and password == users[username]["password"]:
        request.session["role"] = users[username]["role"]

        return RedirectResponse(role_redirects[users[username]["role"]], status_code=303)

    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()

    return RedirectResponse("/", status_code=303)

@app.get("/portfolio")
def portfolio(request: Request):
    role = request.session.get("role")

    content = {
        "about": load_about(),
        "projects": load_projects(),
        "skills": load_skills(),
        "contact": load_contact(),
    }

    if role == "recruiter":
        return templates.TemplateResponse("portfolio.html", {"request": request, "content": content})

    return RedirectResponse("/", status_code=303)

@app.get("/friends")
def friends(request: Request):
    role = request.session.get("role")

    if role == "friends":
        return templates.TemplateResponse("friends.html", {"request": request})

    return RedirectResponse("/", status_code=303)