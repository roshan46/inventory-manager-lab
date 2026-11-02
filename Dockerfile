FROM python:3.13-slim@sha256:27b7c9d4f13ca20bb1170148f02095d50a5dfce1f7f2dabf5ca273727e43b7ea AS builder
WORKDIR /srv
RUN pip install --no-cache-dir uv==0.9.5
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim@sha256:27b7c9d4f13ca20bb1170148f02095d50a5dfce1f7f2dabf5ca273727e43b7ea AS runtime
WORKDIR /srv
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && \
    curl --fail --silent --show-error https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /srv/rds-ca.pem && \
    rm -rf /var/lib/apt/lists/* && useradd --uid 10001 --create-home app
COPY --from=builder /srv/.venv /srv/.venv
COPY app app
ENV PATH="/srv/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s CMD curl --fail --silent http://localhost:8000/health/ready || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-class", "gthread", "--threads", "4", "--access-logfile", "-", "app:create_app()"]
