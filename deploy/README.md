# Running it on the server

Everything on the server runs as rootless Podman containers under one unprivileged user, started by systemd through Quadlet units. This file is the operating manual: where things live, how a deploy works and what has to be done by hand.

The commands in this file run as that user. After switching to it with `sudo`, run `export XDG_RUNTIME_DIR=/run/user/$(id -u)` once, because `sudo` does not set it and `systemctl --user` cannot reach the user's systemd without it.

## Layout

| What | Where on the server |
|---|---|
| Quadlet units (`quadlet/*.container`, `*.volume`, `*.network`) | `~/.config/containers/systemd/` |
| Caddyfile, the app's `.env` and the database connection `wediga-db.env` | `~/wediga-dev/` |
| Database dumps of the app | `~/wediga-dev/backups/` |
| Secrets for the identity provider | `~/authentik/authentik.env`, `~/authentik/authentik-db.env` |
| Setup of the identity provider (`authentik/blueprints/`) | `~/authentik/blueprints/` |
| Database dumps of the identity provider | `~/authentik/backups/` |
| Command of the key for recruiter links (`create-recruiter-link.sh`) | `~/wediga-dev/create-recruiter-link.sh` |
| Backup scripts, services and timers (`systemd/`) | `~/authentik/backup.sh`, `~/wediga-dev/backup.sh`, `~/.config/systemd/user/` |

Caddy is the only container that publishes host ports. Every other container is reached by name over an internal Podman network.

## What a deploy does

A push to `main` builds both app images, scans them and, if the scan passes, triggers the deploy script on the server. The script

1. downloads the Quadlet units, the Caddyfile and the identity provider's setup file from `main`,
2. pins the app units to the images of that commit,
3. restarts `backend-migrate`, which applies new database migrations with `alembic upgrade head`, and then the backend and the frontend.

It does not reload Caddy and it restarts neither the identity provider nor the app's database (`wediga-db`). All of this is deliberate, so a routine deploy of the app cannot take the login, the proxy or the data down.

After a change to the Caddyfile:

```
podman exec caddy caddy validate --config /etc/caddy/Caddyfile
podman exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Changing the identity provider's setup

`authentik/blueprints/wediga.yaml` describes the groups, the mandatory second factor, the recovery flow's second-factor step and the default language. authentik reads the file from `/blueprints/custom` and applies it on startup and whenever it changes.

That file owns what it lists. A change made by hand in the admin interface to one of those settings is reverted the next time the file is applied, so such changes go through the file and a pull request. Accounts, passwords and second factors are not part of it, except for the service account `wediga-dev-hub`.

The hub of wediga.dev uses that account to ask authentik which applications the visitor may use. Its only right is that question, and its token comes from `WEDIGA_HUB_API_TOKEN` in `authentik.env`, which must equal `AUTHENTIK_API_TOKEN` in the app's `.env`. authentik reads both files only when the containers start, so a new value needs a restart of `authentik-server` and `authentik-worker` and of the backend. Like every account in authentik, the service account can create further tokens for itself, each valid for at most a day. If its token may have leaked, a new value alone is therefore not enough: delete the account `wediga-dev-hub` in the admin interface, which removes all of its tokens, set the new value in both files and restart. authentik then creates the account again with the new token.

The recovery flow itself comes from the example blueprint that ships with authentik (`example/flows-recovery-email-verification.yaml`). On a fresh install it has to be created once under Customization, Blueprints and applied there.

The login of wediga.dev signs its tokens with authentik's built-in "authentik Self-signed Certificate". authentik creates that certificate once and never renews it, so it expires on 2027-10-06, but the login keeps working afterwards because neither authentik nor the backend looks at the certificate's dates, only at the key inside it.

Adding someone:

1. Create the user in the admin interface as an internal user, set Locale to `en` and add the group.
2. Create a recovery link on the user's page and pass it on. The link asks for the username, makes them set up a second factor and then lets them choose a password.

Someone lost their authenticator: delete the old device on the user's page under Credentials / Tokens first. A recovery link asks for the second factor before it lets anyone set a password, so without that step the link is useless to them.

## Updating the identity provider

Dependabot does not watch the Quadlet units, so the authentik and PostgreSQL versions are raised by hand.

1. Read the release notes of the new authentik version for breaking changes.
2. Raise the tag and the digest in `authentik-server.container` and `authentik-worker.container`, and in `authentik-test/compose.yaml`. All of them must name the same image, the CI fails otherwise.
3. Merge. The deploy copies the new units to the server but leaves the running containers alone.
4. Take a fresh dump (`systemctl --user start authentik-db-backup.service`).
5. Restart right away, so the new version does not first come up on some later reboot:

```
systemctl --user daemon-reload
systemctl --user restart authentik-server.service authentik-worker.service
```

6. Check `podman logs --tail 30 authentik-server`, log in once and confirm that the second factor is still asked for.

## Updating the app's database

The app has its own PostgreSQL in `wediga-db.container`, separate from the one of the identity provider and only reachable over the internal network. User, database, password, host and port all come from `wediga-db.env`, which the database, the backend and `backend-migrate` read, so they are written down only there. Its version is raised by hand as well. A new minor version (18.6 to 18.7) only needs the tag and the digest raised, a fresh dump and a restart after the merge:

```
systemctl --user start wediga-db-backup.service
systemctl --user daemon-reload
systemctl --user restart wediga-db.service
```

A new major version cannot read the old data directory, so it needs a dump, a new volume and a restore, and gets its own plan.

## Testing the identity provider

`authentik-test/` holds a throwaway authentik with the same images and the same `wediga.yaml` as production. The CI starts it for the end-to-end tests, and it runs locally with Podman, so a change to the setup file or a new version can be tried before it reaches the server. Its secrets and the API key for the setup script are fixed test values in `compose.yaml` and exist nowhere else.

Starting it locally, from the repository root:

```
podman machine start
cd deploy/authentik-test && podman compose up -d && cd ../..
AUTHENTIK_URL=http://localhost:9000 uv run --project backend python deploy/authentik-test/setup.py
```

The first start takes a few minutes. `setup.py` waits until authentik has applied all blueprints, applies the example recovery flow and `wediga.yaml` once more, like on a fresh install, and stops with an error if a blueprint fails. It then creates three accounts (`test-admin` in `wediga-admins`, `test-friend` in `friends`, `test-nogroup` without a group), sets up a TOTP device for each through the real login flow and prints password and TOTP secret. To log in at `http://localhost:9000`, add the secret to an authenticator app by hand. Every run of `setup.py` creates the accounts again with new secrets.

With `AUTHENTIK_ACCOUNTS` set to a file, the script also writes the accounts there, and with `AUTHENTIK_URL` set as well, `npm run e2e` in `frontend/` runs the login smoke test against it:

```
AUTHENTIK_URL=http://localhost:9000 AUTHENTIK_ACCOUNTS=frontend/e2e/.tmp/authentik-accounts.json uv run --project backend python deploy/authentik-test/setup.py
cd frontend && AUTHENTIK_URL=http://localhost:9000 AUTHENTIK_ACCOUNTS=e2e/.tmp/authentik-accounts.json npm run e2e
```

`podman compose down` in `deploy/authentik-test/` stops it, `podman compose down -v` also deletes its data for a fresh start.

## Backup and restore

`authentik-db-backup.timer` writes a dump of the identity provider's database to `~/authentik/backups/` every night, and `wediga-db-backup.timer` does the same for the app's database in `~/wediga-dev/backups/` a quarter of an hour later. Both delete dumps older than 14 days. The dumps stay on the same machine, so they protect against a broken update or a mistake, not against losing the server.

Accounts, groups and settings only exist in the identity provider's database, so its dump is the only copy. The same goes for the app, whose dump holds all of its content and the CV, because the CV lives in the table `cv_document` and not as a file.

Install once:

```
install -m 700 backup.sh ~/authentik/backup.sh
cp authentik-db-backup.service authentik-db-backup.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now authentik-db-backup.timer
```

Restore a dump into the running database, with the server and the worker stopped:

```
systemctl --user stop authentik-server.service authentik-worker.service
podman exec -i authentik-db pg_restore -U authentik -d authentik --clean --if-exists < ~/authentik/backups/authentik-YYYY-MM-DD.dump
systemctl --user start authentik-server.service authentik-worker.service
```

The app's database works the same way, with its own script and units:

```
install -m 700 wediga-db-backup.sh ~/wediga-dev/backup.sh
cp wediga-db-backup.service wediga-db-backup.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now wediga-db-backup.timer
```

Restore a dump with the backend stopped:

```
systemctl --user stop backend.service
podman exec -i wediga-db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < ~/wediga-dev/backups/wediga-YYYY-MM-DD.dump
systemctl --user start backend.service
```

## Ending sessions

Sessions live in the app's database, and the cookie only holds a random token that points at one of them. Deleting a row ends that session with the very next request. Ending every session sends the admin and friends back to the login, and recruiters open their link again, which stays valid:

```
podman exec wediga-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DELETE FROM access.session"'
```

A change in authentik, such as a removed group or a locked account, does not end a running session here, so after such a change I end the sessions of that account by hand. The number at the end is the account's ID in authentik:

```
podman exec wediga-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DELETE FROM access.session s USING access.authentik_login l, access.account a WHERE l.session_id = s.id AND a.id = l.account_id AND a.authentik_user_id = 21"'
```

Expired sessions are deleted by the backend itself once an hour.

## Recruiter links over SSH

Recruiter links can be created without the admin area, through an SSH key that may do nothing else. Its line in `~/.ssh/authorized_keys` starts with `restrict,command="/home/web/wediga-dev/create-recruiter-link.sh"`, so the key gets no shell, no terminal and no forwarding, and every login runs that one script whatever the caller asks for. The script hands the text the caller sent to the backend container as the label, through stdin and never through a shell, and prints the new link, which gets the default lifetime:

```
ssh -i ~/.ssh/wediga_recruiter_link -o IdentitiesOnly=yes web@<server> "Acme Corp"
```

The label must not be empty, longer than 200 characters or contain control characters. Expiry and revoke stay in the admin area. To install or update the script, fetch it from the repository:

```
curl -fsSL https://raw.githubusercontent.com/wediga/wediga-dev/main/deploy/create-recruiter-link.sh -o ~/wediga-dev/create-recruiter-link.sh && chmod 700 ~/wediga-dev/create-recruiter-link.sh
```

To lock the key out, delete its line from `~/.ssh/authorized_keys`. Links it already created stay valid until they are revoked.
