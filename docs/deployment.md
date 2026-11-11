# Deployment

The examples below assume the application is checked out at `/path/to/filer`,
runs as `<your-user>`, serves `/path/to/files`, and listens on port `9000`
behind a reverse proxy.

Read [security-model.md](security-model.md) before exposing the service to a
network. The short version: keep the backend bound to localhost, terminate
TLS at a reverse proxy, and restrict access with a firewall or VPN.

## systemd

Create the credential file. Only root should be able to read it:

```bash
sudo install -m 600 /dev/null /etc/filer.env
echo "FILER_AUTH='<your-user>:<strong-password>'" | sudo tee /etc/filer.env >/dev/null
```

Create `/etc/systemd/system/filer.service`:

```ini
[Unit]
Description=filer
After=network.target

[Service]
Type=simple
User=<your-user>
Group=<your-user>
WorkingDirectory=/path/to/filer
EnvironmentFile=/etc/filer.env
ExecStart=/usr/bin/python3 /path/to/filer/filer.py --dir /path/to/files --bind 127.0.0.1 --port 9000

# Hardening. Adjust ReadWritePaths if the served root or cache is elsewhere.
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/path/to/files /path/to/filer/cache

Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
```

`ProtectHome=read-only` blocks writing to home directories. If the served
files live under `/home`, use `ProtectHome=no` or add explicit
`ReadWritePaths` entries and review the exposure.

The service account needs:

- read access to the served root;
- write access to files that should be editable;
- write access to `cache/` for TTS, Office conversion, articles, and edit
  backups;
- read access to plugin directories, plus write access to plugin `vendor/`
  only during installation.

The service does **not** need to own the entire repository. A dedicated
non-root account is strongly recommended.

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now filer.service
```

## nginx with HTTPS

The application speaks plain HTTP and must stay bound to localhost. Terminate
TLS in nginx and proxy to it.

```nginx
server {
    listen 80;
    server_name files.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name files.example.com;

    ssl_certificate     /etc/letsencrypt/live/files.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/files.example.com/privkey.pem;

    # Uploads are limited to 256 MiB. Edit requests are limited to 16 MiB.
    client_max_body_size 256m;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

Reload nginx after changing the configuration:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Caddy

Caddy can obtain and renew certificates automatically:

```caddyfile
files.example.com {
    reverse_proxy 127.0.0.1:9000
}
```

## Editing and backups

If editing is enabled, the service account must be able to write to the
files being edited. Before each save, filer copies the original to
`cache/edit-backups/`.

- Back up the served directory independently. `cache/edit-backups/` is a
  convenience, not a backup system.
- Do not run the service as root just to make files writable. Fix ownership
  and permissions instead.
- Files are edited through atomic replacement in the same directory. The
  service account needs write permission on the directory, not only on the
  file.
- Symbolic links are not editable.
- If the file changes externally, the save is rejected with `409`.

## Plugins

Plugins are trusted Python code loaded from `plugins/` or `--plugins-dir`.
They run in the service process with the service account's permissions.

- Review plugin code before installing it.
- Keep plugin directories writable only by the administrator.
- Plugin `vendor/` packages are imported by the service. Treat them like
  application dependencies.
- Use `--no-plugins` to disable all plugins during incident response.
- Plugin routes use `/plugins/<id>/...` and require the same Basic Auth.

## Troubleshooting

If the service does not start, check its state first:

```bash
systemctl status filer.service
journalctl -u filer.service -n 100 --no-pager
```

Common causes:

- `/etc/filer.env` is missing, unreadable, or does not contain a valid
  `FILER_AUTH` value (`DL_AUTH` is accepted as a fallback).
- The run user cannot read the configured file root.
- The run user cannot write to the served directory for editing.
- The port is already in use or the reverse proxy points at the wrong
  address.
- A plugin failed to load; look for `filer: plugin ... skipped` in the logs.
- `cache/` is not writable, so backups or optional features fail.
- systemd hardening blocks a path; adjust `ReadWritePaths`.
