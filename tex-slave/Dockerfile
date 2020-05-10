FROM python:3-alpine

# install packages for aiohttp + tex

RUN apk add gcc musl-dev poppler poppler-utils texlive texmf-dist-formatsextra texmf-dist-games texmf-dist-humanities texmf-dist-latexextra texmf-dist-music texmf-dist-pictures texmf-dist-pstricks texmf-dist-science texlive-xetex
RUN pip install --no-cache-dir aiohttp
RUN apk del musl-dev gcc

WORKDIR /usr/src/texsrc

COPY slave.py .

CMD ["python", "slave.py"]
