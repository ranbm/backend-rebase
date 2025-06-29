FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools and deps
COPY pyproject.toml setup.cfg ./
RUN pip install --no-cache-dir .

# Copy actual source
COPY users/ users/

# Run app as module
CMD ["python", "-m", "users.app"]
