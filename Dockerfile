FROM python:3.9-slim

COPY ./server /src/server
COPY ./requirements.txt /src
COPY ./.env /src/.env
COPY ./final.csv /src/final.csv

WORKDIR /src

RUN pip3 install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host=0.0.0.0", "--reload"]
