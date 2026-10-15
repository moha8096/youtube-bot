FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# نصب deno به /usr/local
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

# تست
RUN deno --version

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
