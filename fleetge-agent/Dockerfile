FROM python:3.11-slim

# Copy docker and docker-compose-plugin from the official docker image
COPY --from=docker:latest /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:latest /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default configuration environment variables
ENV PORT=8080
ENV STACKS_BASE_DIR=/opt/stacks
ENV AGENT_TOKEN=""
ENV AGENT_REQUIRE_TOKEN=true

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
