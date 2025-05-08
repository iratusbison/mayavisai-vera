FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libtiff-dev \
    libwebp-dev \
    tcl-dev \
    tk-dev \
    python3-tk \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

EXPOSE 8000

# Run Django with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "multiuser.wsgi:application"]
