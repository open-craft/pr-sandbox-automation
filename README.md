# pr-sandbox-automation

Automatically manage sandboxes for PRs

## Dev

1. Update the dev secrets and `dev.env` file with the correct Github app details.
2. Setup the dev environment

  ```shell
  docker compose up -d
  ```

1. Run migrations

  ```shell
  docker exec pr-sandbox-automation-dev-app uv run alembic upgrade head
  ```

1. Use a proxy service like [smee.io](https://smee.io/) to pipe in webhook
   requests to you dev app

   ```shell
   smee -u https://smee.io/<channel id 1> -t http://127.0.0.1:8900/github-webhook/
   smee -u https://smee.io/<channel id 2> -t http://127.0.0.1:8900/argocd-webhook/
   ```

### Install pre-commit

This repo uses [pre-commit](https://pre-commit.com/) to ensure the code is
formatted and up to standards before it is being committed.

1. Install pre-commit using `uv tool install pre-commit`
2. Once pre-commit is installed, execute `pre-commit install` to setup the git
   commit hooks.
3. Execute `pre-commit install -t commit-msg` to allow the `commit-msg` state.

## Migration

### Create migration

```shell
docker exec pr-sandbox-automation-dev-app uv run alembic revision \
  --autogenerate \
  -m "Comment to explain details of the migration"
```

### Run migration

```shell
docker exec pr-sandbox-automation-dev-app uv run alembic upgrade head
```

## Container image

Build the production image:

```shell
docker build -t pr-sandbox-automation:local .
```

For local development, Docker Compose uses `Dockerfile.dev` automatically:

```shell
docker compose up -d
```

## Helm chart

The chart lives at `charts/pr-sandbox-automation`. By default, it expects the
required secrets to be provided as **Kubernetes Secrets** and mounted as files.

### Required secrets

Each secret should expose a key with the same name so it becomes a file in
`/var/run/secrets/pr-sandbox`:

- `pr-sandbox-github-webhook-secret`
- `pr-sandbox-github-private-key`
- `pr-sandbox-pr-installation-id`
- `pr-sandbox-cluster-installation-id`
- `pr-sandbox-mysql-connection-string`
- `pr-sandbox-argocd-webhook-auth`

Example creation (one secret per key):

```shell
kubectl create secret generic pr-sandbox-github-webhook-secret \
  --from-literal=pr-sandbox-github-webhook-secret='...'
```

If you use a single Secret with all keys instead, update `secretMounts` in
`values.yaml` accordingly.

### Install

<!-- markdownlint-disable MD013 -->
```shell
helm install pr-sandbox-automation charts/pr-sandbox-automation \
  --set env.PR_SANDBOX_GITHUB_APP_IDENTIFIER=12345 \
  --set env.PR_SANDBOX_CLUSTER_GITHUB_REPO_URL=https://github.com/example/cluster.git \
  --set env.PR_SANDBOX_ARGOCD_APP_URL=https://argocd.example.com \
  --set env.PR_SANDBOX_APP_LOGS_URL=https://pr-sandbox.example.com/web/logs
```
<!-- markdownlint-enable -->

### Optional MySQL subchart (disabled by default)

```shell
helm install pr-sandbox-automation charts/pr-sandbox-automation \
  --set mysql.enabled=true \
  --set mysql.auth.password='change-me'
```

This creates the `pr-sandbox-mysql-connection-string` secret that the app reads
at startup.

## Published artifacts

- Image: `ghcr.io/open-craft/pr-sandbox-automation:<tag>`
- Helm chart (OCI): `oci://ghcr.io/open-craft/charts/pr-sandbox-automation`
