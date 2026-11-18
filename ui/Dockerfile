FROM python:3.11-slim

RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

USER app
EXPOSE 8050
CMD ["gunicorn", "-b", "0.0.0.0:8050", "-w", "2", "-k", "gthread", "--threads", "4", "--timeout", "15", "--graceful-timeout", "5", "--keep-alive", "2", "--limit-request-line", "1024", "--limit-request-fields", "50", "--worker-tmp-dir", "/dev/shm", "app:app"]
