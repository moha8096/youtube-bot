FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# نصب deno
ENV DENO_INSTALL="/root/.deno"
RUN curl -fsSL https://deno.land/install.sh | sh
ENV PATH="${DENO_INSTALL}/bin:${PATH}"

# تست deno
RUN deno --version

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# به yt-dlp بگو deno کجاست
ENV YT_DLP_JS_RUNTIMES="deno:/root/.deno/bin/deno"

COPY . .

CMD ["python", "bot.py"]
