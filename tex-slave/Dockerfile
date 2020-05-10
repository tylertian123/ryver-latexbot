FROM python:3-alpine

# install packages for aiohttp + tex

RUN apk add gcc musl-dev texlive-full poppler poppler-utils
RUN pip install --no-cache-dir aiohttp
RUN apk del musl-dev gcc

WORKDIR /usr/src/texsrc

COPY slave.py .

CMD ["python", "slave.py"]
