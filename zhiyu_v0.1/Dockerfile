FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements-runtime.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements-runtime.lock
COPY requirements-build.lock ./
RUN --mount=type=cache,target=/root/.cache/pip pip install --timeout 120 --retries 5 --require-hashes -r requirements-build.lock
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN pip install --no-cache-dir --no-build-isolation --no-deps .
COPY alembic.ini ./
COPY migrations ./migrations
COPY config ./config
COPY tools ./tools
COPY tests/fixtures/golden_chain_m2.json ./tests/fixtures/golden_chain_m2.json
RUN useradd --create-home --uid 10001 zhiyu
USER zhiyu
CMD ["uvicorn", "zhiyu.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS tests
USER root
COPY requirements-operator.lock ./
COPY requirements-dev.lock ./
RUN --mount=type=cache,target=/root/.cache/pip pip install --timeout 120 --retries 5 --require-hashes -r requirements-dev.lock
COPY tests ./tests
COPY baseline ./baseline
COPY tools ./tools
COPY docker-compose.yml docker-compose.ai.yml ./
RUN mkdir -p /app/artifacts/v0.9 && chown -R zhiyu:zhiyu /app/artifacts
USER zhiyu
ENV PYTEST_ADDOPTS="-p no:cacheprovider --strict-markers" ZHIYU_REQUIRE_POSTGRES=1
CMD ["python", "-m", "pytest", "-q", "-m", "not compose"]
