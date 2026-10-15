FROM denoland/deno:latest AS deno
FROM python:3.11-slim

# کپی deno از image رسمی
COPY --from=deno /usr/bin/deno /usr/local/bin/deno

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN deno --version

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
