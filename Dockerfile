FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so this layer is cached unless
# requirements.txt changes. All dependencies ship manylinux wheels,
# so no compilers or build tools are needed in the image.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The application is a single module; copy only what runtime needs.
# Tests, docs, and dev tooling stay out of the production image.
COPY main.py .

# Run the application as an unprivileged user.
RUN groupadd --system app && useradd --system --gid app app
USER app

EXPOSE 8000

# Uses the Python standard library only, so no extra packages
# (curl/wget) are required in the image.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
