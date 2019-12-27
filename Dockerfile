FROM python:3-alpine

WORKDIR /usr/src/latexbot

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apk add curl

COPY . .

CMD [ "python", "./latexbot.py" ]
