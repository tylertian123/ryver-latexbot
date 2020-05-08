FROM python:3-alpine

WORKDIR /usr/src/latexbot

COPY requirements.txt ./
RUN apk add gcc
RUN apk add musl-dev
RUN apk add curl
RUN pip install --no-cache-dir -r requirements.txt
RUN apk del musl-dev
RUN apk del gcc

COPY . .

CMD [ "python", "./latexbot.py" ]
