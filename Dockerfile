FROM python:alpine
LABEL name="img-ocr-validator"
LABEL description="An image OCR validator to ensure images have proper HTML alt tags, otherwise they are logged in a CSV file."
LABEL maintainer="hashsploit <hashsploit@protonmail.com>"

# Install dependencies
RUN apk --update add libxml2-dev libxslt-dev libffi-dev gcc musl-dev libgcc openssl-dev curl bash \
	&& apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev py3-pip tesseract-ocr g++ make enchant2-dev aspell-en

WORKDIR /root

ADD requirements.txt .

RUN cd /root && pip install -r requirements.txt

# Use the URLS environment variable
ENV ARGS=""

CMD /bin/bash ./launch.sh ${ARGS}

