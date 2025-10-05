FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
COPY ./wait-for-it.sh /
RUN chmod +x /wait-for-it.sh

CMD [ "sh", "-c", "/wait-for-it.sh db_service:5432 -t 120 --strict -- flask db upgrade && python run.py" ]
