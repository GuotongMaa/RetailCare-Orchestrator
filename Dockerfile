FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements.txt pyproject.toml ./
RUN pip install -U pip && pip install -r requirements.txt

COPY src ./src
COPY eval ./eval
RUN pip install -e .

EXPOSE 8080
CMD ["uvicorn", "retailcare.api.app:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "src"]
