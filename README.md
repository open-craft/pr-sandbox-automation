# pr-sandbox-automation
Automatically manage sandboxes for PRs


## Dev
1. Update the dev secrets and `dev.env` file with the correct Github app details.
2. Setup the dev environment

```
docker compose up -d
```

3. Run migrations

```
docker exec pr-sandbox-automation-dev-app uv run alembic upgrade head
```

4. Use a proxy service like [smee.io](https://smee.io/) to pipe in webhook requests to you dev app
```
smee -u https://smee.io/<channel id 1> -t http://127.0.0.1:8000/github-webhook/
smee -u https://smee.io/<channel id 2> -t http://127.0.0.1:8000/argocd-webhook/
```

### Install pre-commit

This repo uses [pre-commit](https://pre-commit.com/) to ensure the code is formatted and up to standards before it is being committed.

1. Install pre-commit using `uv tool install pre-commit`
2. Once pre-commit is installed, execute `pre-commit install` to setup the git commit hooks.
3. Execute `pre-commit install -t commit-msg` to allow the `commit-msg` state.


## Migration

### Create migration

```
docker exec pr-sandbox-automation-dev-app uv run alembic revision --autogenerate -m "Comment to explain details of the migration"
```

### Run migration

```
docker exec pr-sandbox-automation-dev-app uv run alembic upgrade head
```
