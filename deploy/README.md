# Running it on the server

Everything on the server runs as rootless Podman containers under one unprivileged user, started by systemd through Quadlet units. This file is the operating manual: where things live, how a deploy works and what has to be done by hand.

## Layout

| What | Where on the server |
|---|---|
| Quadlet units (`quadlet/*.container`, `*.volume`, `*.network`) | `~/.config/containers/systemd/` |
| Caddyfile and the app's `.env` | `~/wediga-dev/` |
| Secrets for the identity provider | `~/authentik/authentik.env`, `~/authentik/authentik-db.env` |
| Setup of the identity provider (`authentik/blueprints/`) | `~/authentik/blueprints/` |
| Database dumps of the identity provider | `~/authentik/backups/` |
| Backup script, service and timer (`systemd/`) | `~/authentik/backup.sh`, `~/.config/systemd/user/` |

Caddy is the only container that publishes host ports. Every other container is reached by name over an internal Podman network.

## What a deploy does

A push to `main` builds both app images, scans them and, if the scan passes, triggers the deploy script on the server. The script

1. downloads the Quadlet units, the Caddyfile and the identity provider's setup file from `main`,
2. pins the app units to the images of that commit,
3. restarts the backend and the frontend.

It does not reload Caddy and it does not restart the identity provider. Both are deliberate, so a routine deploy of the app cannot take the login or the proxy down.

After a change to the Caddyfile:

```
podman exec caddy caddy validate --config /etc/caddy/Caddyfile
podman exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Changing the identity provider's setup

`authentik/blueprints/wediga.yaml` describes the groups, the mandatory second factor, the recovery flow's second-factor step and the default language. authentik reads the file from `/blueprints/custom` and applies it on startup and whenever it changes.

That file owns what it lists. A change made by hand in the admin interface to one of those settings is reverted the next time the file is applied, so such changes go through the file and a pull request. Accounts, passwords and second factors are not part of it.

The recovery flow itself comes from the example blueprint that ships with authentik (`example/flows-recovery-email-verification.yaml`). On a fresh install it has to be created once under Customization, Blueprints and applied there.

Adding someone:

1. Create the user in the admin interface as an internal user, set Locale to `en` and add the group.
2. Create a recovery link on the user's page and pass it on. The link asks for the username, makes them set up a second factor and then lets them choose a password.

Someone lost their authenticator: delete the old device on the user's page under Credentials / Tokens first. A recovery link asks for the second factor before it lets anyone set a password, so without that step the link is useless to them.

## Updating the identity provider

Dependabot does not watch the Quadlet units, so the authentik and PostgreSQL versions are raised by hand.

1. Read the release notes of the new authentik version for breaking changes.
2. Raise the tag and the digest in `authentik-server.container` and `authentik-worker.container`. Both must name the same image.
3. Merge. The deploy copies the new units to the server but leaves the running containers alone.
4. Take a fresh dump (`systemctl --user start authentik-db-backup.service`).
5. Restart right away, so the new version does not first come up on some later reboot:

```
systemctl --user daemon-reload
systemctl --user restart authentik-server.service authentik-worker.service
```

6. Check `podman logs --tail 30 authentik-server`, log in once and confirm that the second factor is still asked for.

## Backup and restore

`authentik-db-backup.timer` writes a dump of the database to `~/authentik/backups/` every night and deletes dumps older than 14 days. The dumps stay on the same machine, so they protect against a broken update or a mistake, not against losing the server.

Accounts, groups and settings only exist in the database, so the dump is the only copy.

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
