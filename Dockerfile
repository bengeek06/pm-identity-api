FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
COPY ./wait-for-it.sh /
RUN chmod +x /wait-for-it.sh

CMD [ "sh", "-c", "/wait-for-it.sh identity_db:5432 --timeout=60 --strict -- flask db upgrade && python run.py" ]
