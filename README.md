# Netcool DASH LTPA Auth – Python 3.6 Flask App

End‑to‑end example that authenticates via IBM Netcool DASH's LTPA token and fetches username + roles.

## Quickstart (local)
```bash
python3 -m pip install -r requirements.txt
export FLASK_SECRET_KEY="change-me"
export DASH_HOST_IP="10.0.0.5"
export DASH_HOST_PORT="443"
export DASH_INTEGRATION_SERVICE="ltpa-integration/validate"
export LTPA_TOKEN_NAME="LtpaToken2"
export VERIFY_TLS="true"
export TIMEOUT_SECONDS="5"
python run.py
# Open http://localhost:5000/whoami (requires valid LTPA), /dashboard for RBAC example
```

## Docker
```bash
docker build -t tce-ltpa:latest .
docker run -p 5000:5000 --rm   -e FLASK_SECRET_KEY=change-me   -e DASH_HOST_IP=10.0.0.5   -e DASH_HOST_PORT=443   -e DASH_INTEGRATION_SERVICE='ltpa-integration/validate'   -e LTPA_TOKEN_NAME='LtpaToken2'   tce-ltpa:latest
```

## Tests
```bash
python3 -m pip install -r requirements-dev.txt
pytest -q
```

## Docker Compose
```bash
cp .env.example .env
docker compose up --build
```

## Helm (from source tree)
See `charts/tce-ltpa/values.yaml` for options.
```bash
helm upgrade --install tce charts/tce-ltpa   --set image.repository=ghcr.io/your-org/tce-ltpa   --set image.tag=1.0.0   --set ingress.enabled=true   --set ingress.className=nginx   --set ingress.hosts[0].host=app.example.com   --set flaskSecret.value="$(openssl rand -hex 32)"
```

## CI / Release
- CI runs on push/PR: tests + Docker build (`.github/workflows/ci.yml`).
- Release on tag (e.g., `v1.2.3`): pushes Docker to GHCR, packages/pushes Helm chart to GHCR OCI, uploads chart to GitHub Release (`.github/workflows/release.yml`).

---

Security notes:
- Keep TLS verification enabled in production. If DASH uses a private CA, set `CA_BUNDLE_PATH` or mount a Secret and set `REQUESTS_CA_BUNDLE`.
- Ensure this app and DASH share an SSO boundary/domain as required by your LTPA setup.
