FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot1_hamal_live.py .
COPY shabbat.py .
COPY hourly_updates.py .
COPY haredi_updates.py .
RUN mkdir -p logs
# הפורט בפועל נקבע ע"י משתנה הסביבה PORT (ברירת מחדל 10000 בקוד עצמו)
ENV PORT=10000
EXPOSE 10000
CMD ["python", "-u", "bot1_hamal_live.py"]
