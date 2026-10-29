FROM python:3.12-slim
WORKDIR /code
# ffmpeg lets the transcription service transcode browser audio (webm/opus) into a
# format the Gemini audio model reliably decodes (16 kHz mono WAV).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Download the pinned face models before copying app code, so code changes reuse this cached layer.
COPY app/scripts/download_face_models.py /tmp/download_face_models.py
RUN FACE_MODELS_DIR=/opt/recruito/models python /tmp/download_face_models.py && rm /tmp/download_face_models.py
COPY app ./app
COPY policies ./policies
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
