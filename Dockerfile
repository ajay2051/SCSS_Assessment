FROM python:3.10.3-slim-buster

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && cat apt_requirements.txt | xargs apt -y --no-install-recommends install libmagic-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt autoremove \
    && apt autoclean

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip uvicorn \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

RUN chmod +x /usr/src/app/entrypoint.sh

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]