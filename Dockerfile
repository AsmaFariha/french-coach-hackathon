FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download fr_core_news_sm

COPY . .

EXPOSE 7860

CMD ["python", "app_custom.py"]
