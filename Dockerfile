FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot1_hamal_live.py .
COPY shabbat.py .

RUN mkdir -p logs

CMD ["python", "-u", "bot1_hamal_live.py"]
