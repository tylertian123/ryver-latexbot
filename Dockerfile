FROM python:3-alpine

WORKDIR /usr/src/latexbot

COPY . .
RUN apk add gcc musl-dev
RUN pip install --no-cache-dir -r requirements.txt
RUN apk del gcc musl-dev

CMD [ "python", "./latexbot/main.py" ]
