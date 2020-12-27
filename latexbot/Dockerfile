FROM python:3-alpine

RUN apk add gcc musl-dev

# Install deps
WORKDIR /usr/src/latexbot
COPY requirements.txt .
RUN pip install -r requirements.txt && apk del gcc musl-dev

COPY setup.py MANIFEST.in ./
COPY latexbot/ ./latexbot
RUN pip install . && rm -rf *

# No buffering for immediate log output
ENV PYTHONUNBUFFERED=1
CMD ["python3", "-m", "latexbot"]
