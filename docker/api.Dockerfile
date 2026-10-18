# Build from the repository root: docker build -f docker/api.Dockerfile -t ausold-api .
FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install ".[api]"

FROM python:3.12-slim
RUN useradd --system --uid 10001 app
COPY --from=build /install /usr/local
USER app
ENV PYTHONUNBUFFERED=1 AUTH_MODE=entra ENVIRONMENT=prod
EXPOSE 8000
CMD ["uvicorn", "au_sold_prices.api.app:build_default_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
