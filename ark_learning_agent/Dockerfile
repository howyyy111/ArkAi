FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ARKAIS_AGENT_HOST=0.0.0.0 \
    ARKAIS_AGENT_WITH_UI=true \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

RUN mkdir -p /app/ark_learning_agent
COPY . /app/ark_learning_agent/

EXPOSE 8000

# Start the application using uvicorn. 
# We use the shell form to allow the $PORT environment variable expansion from Cloud Run.
CMD uvicorn ark_learning_agent.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
