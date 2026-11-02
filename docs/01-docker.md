# 1 — Learn Docker with a working app

## Prerequisites and cost

Docker Desktop must be running with Linux containers. Run commands from the project root in PowerShell. This lesson needs no AWS account. Local port 8001 avoids the original order lab's port 8000.

## Build and inspect

An **image** is a packaged filesystem plus startup metadata. A **container** is an instance of that image. A **volume** stores data outside a container's replaceable filesystem.

```powershell
docker compose config
docker compose build
docker compose up -d --wait
docker compose ps
docker compose images
docker compose logs --tail 30 app
docker compose exec app id
docker compose exec app sh
```

Inside the shell, run `pwd`, `ls`, and `exit`. The app runs as UID 10001, not root. Visit http://localhost:8001, create a product, and adjust its stock.

Read the Dockerfile from top to bottom. The builder installs dependencies from `uv.lock`; the runtime copies only the virtual environment and app. Copying dependency manifests before source means source-only changes can reuse the dependency layer. `.dockerignore` keeps state, credentials, local virtual environments, and Git history out of the build context. `EXPOSE 8000` documents the container port; Compose's `127.0.0.1:8001:8000` actually publishes it on the host.

**Exercise:** change a template sentence, rebuild, and inspect which steps say `CACHED`. **Hint:** dependency installation should remain cached. **Solution:** source `COPY` and subsequent layers rebuild; undo the sentence afterward.

## Networks and configuration

```powershell
docker compose exec app python -c "import socket; print(socket.gethostbyname('db'))"
docker compose exec db psql -U lab -d inventory -c 'select code, stock from product;'
```

Compose provides DNS for service names. The database host is `db`, not `localhost`: each container has its own loopback interface. The database port is not published to your laptop. Local credentials in Compose are explicitly demo-only; AWS uses Secrets Manager at runtime.

## Persistence experiment

```powershell
docker compose up -d --force-recreate app db
docker compose down
docker compose up -d --wait
```

Expected: product data and history still exist. Container IDs change; the named PostgreSQL volume stays. **Hint:** inspect `docker volume ls` and `docker compose config`. **Solution:** the database files live at the volume mount, not in the image. Do not run `down --volumes` until you intend to reset data.

## Break: port already in use

With the app running:

```powershell
docker run --rm --name inventory-port-conflict -p 127.0.0.1:8001:80 nginx:alpine
```

Expected: Docker cannot bind the occupied host port. **Hint:** compare host and container ports. **Solution:** run the second container on `8002:80`, or remove its published port. If the failed start left a container, remove that specifically named container with `docker rm inventory-port-conflict`. Do not stop unrelated applications to fix this exercise.

## Break: database unavailable

```powershell
docker compose stop db
curl.exe -i http://localhost:8001/health/live
curl.exe -i http://localhost:8001/health/ready
docker compose logs --tail 30 app
docker compose start db
```

Expected: liveness stays 200; readiness becomes 503; readiness returns to 200 after PostgreSQL starts. **Hint:** a running process need not be ready for traffic. **Solution:** restart the database; do not rebuild the image or delete its volume.

To see an incorrect connection host, run a disposable app container:

```powershell
docker compose run --rm -e DATABASE_URL=postgresql+psycopg://lab:local-only@localhost:5432/inventory app flask --app app init-db
```

Expected: connection failure. The one-off override disappears with the container. Retry without `-e` to use `db` and succeed.

## Checkpoint and reset

Explain image layers, port mapping, service DNS, environment variables, health checks, and volume lifetime. Confirm data survives recreation. Run `docker compose down` to stop. To deliberately start empty, use `docker compose down --volumes` and then `up --build -d --wait`.
