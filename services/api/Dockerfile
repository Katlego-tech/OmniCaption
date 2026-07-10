# OmniCaption backend API — lightweight, model-free bridge service.
# Deployable anywhere (Railway, Fly.io, any Docker host); no GPU required.
FROM python:3.11-slim

WORKDIR /srv/api

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
