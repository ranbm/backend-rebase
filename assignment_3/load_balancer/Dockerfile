FROM python:3.11-slim

WORKDIR /app

COPY config.py ./assignment_3/config.py
COPY __init__.py ./assignment_3/__init__.py

COPY load_balancer/ ./load_balancer/

RUN touch ./assignment_3/__init__.py
RUN touch ./load_balancer/__init__.py

COPY load_balancer/pyproject.toml load_balancer/setup.cfg ./

RUN pip install uv

RUN uv pip install -e . --system
EXPOSE 40001
CMD ["python", "-m", "load_balancer.app"]