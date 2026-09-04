# Senus Board Report — backend Dockerfile
# Builds a container that runs the FastAPI API. Deployed as a Render web
# service; see render.yaml at the repo root and README.md § Deployment.

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer across builds
# that only change application code, not requirements.txt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code, seed data, and the entrypoint script.
COPY . .
RUN chmod +x entrypoint.sh

# Render sets $PORT at runtime and routes external traffic to it; 8000 here
# is just the documented default for local `docker run` without Render.
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]