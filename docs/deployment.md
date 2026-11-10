# Deployment

The examples below assume the application is checked out at `/path/to/filer`, runs as `<your-user>`, serves `/path/to/files`, and listens on port `9000` behind a reverse proxy.

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
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now filer.service
```

## nginx with HTTPS

The application speaks plain HTTP and must stay bound to localhost. Terminate TLS in nginx and proxy to it.

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

## Troubleshooting

If the service does not start, check its state first:

```bash
systemctl status filer.service
journalctl -u filer.service -n 100 --no-pager
```

Common causes:

- `/etc/filer.env` is missing, unreadable, or does not contain a valid `FILER_AUTH` value (`DL_AUTH` is accepted as a fallback).
- The run user cannot read the configured file root.
- The port is already in use or the reverse proxy points at the wrong address.
