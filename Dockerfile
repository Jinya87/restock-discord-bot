FROM mcr.microsoft.com/playwright/python:v1.55.0-noble
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY monitor.py bot.py stock-state.json ./
ENV PYTHONUNBUFFERED=1
ENV CHECK_INTERVAL_SECONDS=30
CMD ["python", "bot.py"]
