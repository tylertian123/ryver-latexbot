FROM python:3-alpine

WORKDIR /usr/src/latexbot

COPY requirements.txt ./
RUN apk add gcc musl-dev
RUN pip install --no-cache-dir -r requirements.txt
RUN apk del gcc musl-dev

COPY . .

CMD [ "python", "./latexbot.py" ]
