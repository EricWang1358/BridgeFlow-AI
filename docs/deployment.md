# Self-hosting

The files in `deploy/` are templates for a Linux host using systemd and Caddy. Adapt the service account, filesystem paths and domain to your installation. They do not contain a production hostname, tenant identity or access credential.

## Private instance configuration

Keep `env.sh`, signing keys, real dictionaries, access policy, seat capacity and runtime data out of source control. The repository supplies placeholder examples:

```bash
cp data/mappings/access-control.example.yaml data/mappings/access-control.yaml
cp data/mappings/seats.example.yaml data/mappings/seats.yaml
```

Replace every wiki-space placeholder in the access policy with an ID from your own tenant. Review role grants, including `console_access`, before use. Alternatively set `ACCESS_CONTROL_PATH` to an external configuration file. A missing or invalid access policy fails closed.

For a seat fleet, use `scripts/provision_seat.sh --init N` on the configured host to generate absolute home paths and ports. The registry and person-to-seat assignments are private installation data. Back them up outside the repository. The deploy script preserves access policy and seat capacity across source updates, including the transition from earlier versions that tracked them.

## Portal and staff access

Install `portal/` into the service's virtual environment. Configure your own Feishu application's OAuth callback and scopes. The portal requires `PORTAL_FEISHU_APP_ID`, `PORTAL_FEISHU_APP_SECRET`, `PORTAL_KEY_PATH`, `PORTAL_SESSION_SECRET` and `PORTAL_EXTERNAL_BASE_URL` in the launching environment. Generate the signing key outside the repository with `python -m portal_app.keygen /private/path/portal-key.pem`.

Set `PORTAL_APPS_PATH` to your private application registry. `portal/apps.yaml` is a localhost development example. Configure the backend's `PORTAL_BASE_URL` and the portal's console-check route for your deployment. Use HTTPS, secure cookies and the Caddy forward-auth configuration for staff entry. See [portal documentation](../portal/README.md).

## Services and guest mode

The supplied units cover the backend, portal, per-seat Web runtimes, optional guest instance, guest reset timer and model gate. Keep their backend listeners on loopback and expose the reverse proxy instead.

Guest mode is optional and isolated from employee files. AI is off unless explicitly enabled. For guest AI, configure the model gate, its private provider credential and the guest client token; review `data/mappings/llm-gate.yaml` for model allowlisting, rate limits and token limits. Configure a budget if required by your installation. Never pass the provider key directly to the guest process.

Render Caddy configuration for your domain with `deploy/render_caddy.py`; pass `--seats` for your registry and `--guest-port` only when the guest service is ready. Check configuration before reloading services. `deploy/preflight.sh` checks the assembled installation.

## GitHub Actions

The workflow runs tests on pull requests and main-branch pushes. Deployment is opt-in through the `DEPLOY_ENABLED` repository variable. An enabled installation also needs `PUBLIC_DOMAIN` and the `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` secrets. `FIELD_DICTIONARY_YAML` is an optional environment secret for dictionary synchronization.

The deployment job sends the tested commit to `deploy/deploy.sh`, rebuilds dependencies and the client bundle, then performs liveness and instance checks. Source publication does not configure a tenant, provision a host or grant access to a running instance.
