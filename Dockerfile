FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# نصب deno
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh \
    && chmod +x /usr/local/bin/deno

# تست deno
RUN /usr/local/bin/deno --version

# نصب yt-dlp از pip
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# به yt-dlp بگو deno کجاست
ENV YT_DLP_JS_RUNTIMES="deno:/usr/local/bin/deno"

COPY . .

CMD ["python", "bot.py"]
