FROM python:3.11-slim

WORKDIR /app

COPY config.py ./assignment_3/config.py
COPY __init__.py ./assignment_3/__init__.py

COPY file_management/ ./file_management/

RUN touch ./assignment_3/__init__.py
RUN touch ./file_management/__init__.py
RUN touch ./file_management/api/__init__.py
RUN touch ./file_management/api/v0/__init__.py

COPY file_management/pyproject.toml file_management/setup.cfg ./

RUN pip install uv

RUN uv pip install -e . --system
EXPOSE 50001
CMD ["python", "-m", "file_management.app"]