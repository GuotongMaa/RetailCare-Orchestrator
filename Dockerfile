FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements.txt pyproject.toml ./
RUN pip install -U pip && pip install -r requirements.txt

COPY src ./src
COPY eval ./eval
COPY web ./web
RUN pip install -e .

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"
CMD ["uvicorn", "retailcare.api.app:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "src"]
