import re
import json
import subprocess
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ───────────────────────────────
TOKEN = "8958356993:AAGtrCWiHIlX_XfMMlwT1SpEMkFR4VYAIlc"
COOKIES = "/app/cookies.txt"
# ───────────────────────────────

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(m\.)?'
    r'(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+'
)

QUALITY_ORDER = ['2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p']


def get_links(url: str):
    cmd = [
        "yt-dlp",
        "--cookies", COOKIES,
        "--extractor-args", "youtube:player_client=tv_embedded",
        "--dump-json",
        "--no-playlist",
        url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr.strip()[-500:])

    info = json.loads(result.stdout)
    title = info.get('title', 'بدون عنوان')
    duration = info.get('duration_string', '?')
    thumbnail = info.get('thumbnail', '')

    # فرمت‌های merged (ویدیو + صدا توی یه فایل)
    merged = []
    seen = set()

    for f in info.get('formats', []):
        note = f.get('format_note', '')
        ext = f.get('ext', '')
        direct_url = f.get('url', '')
        size = f.get('filesize') or f.get('filesize_approx') or 0
        vcodec = f.get('vcodec', 'none')
        acodec = f.get('acodec', 'none')

        if not direct_url: continue
        if vcodec == 'none': continue
        if acodec == 'none': continue
        if ext not in ('mp4', 'webm'): continue
        if note in seen: continue

        seen.add(note)
        size_mb = f"{size/1024/1024:.1f} MB" if size else "؟"

        # تعیین کیفیت از height اگه note خالی بود
        if not note:
            height = f.get('height', 0)
            if height: note = f"{height}p"
            else: continue

        merged.append({
            'q': note,
            'ext': ext,
            'size': size_mb,
            'url': direct_url,
            'height': f.get('height', 0)
        })

    # مرتب از بهترین به پایین
    merged.sort(key=lambda x: x.get('height', 0), reverse=True)

    return title, duration, thumbnail, merged


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = YOUTUBE_REGEX.search(text)

    if not match:
        await update.message.reply_text("❌ لینک یوتیوب معتبر نیست.")
        return

    url = match.group(0)
    if not url.startswith('http'):
        url = 'https://' + url

    msg = await update.message.reply_text("⏳ در حال پردازش...")

    try:
        title, duration, thumbnail, formats = get_links(url)

        if not formats:
            await msg.edit_text(
                "⚠️ فرمت merged پیدا نشد.\n"
                "یوتیوب برای این ویدیو فقط استریم جداگانه داره.\n"
                "برای کیفیت بالا باید ffmpeg نصب باشه."
            )
            return

        lines = [
            f"🎬 *{title}*",
            f"⏱ مدت: `{duration}`",
            f"📊 بهترین کیفیت موجود: `{formats[0]['q']}`",
            ""
        ]

        for f in formats:
            lines.append(
                f"📥 [{f['q']} {f['ext'].upper()} — {f['size']}]({f['url']})"
            )

        lines += [
            "",
            "⚠️ لینک‌ها ۶ ساعت معتبرن.",
            "برای دانلود از 1DM یا IDM استفاده کن."
        ]

        await msg.edit_text(
            "\n".join(lines),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    except Exception as e:
        await msg.edit_text(
            f"❌ خطا:\n`{str(e)[:400]}`",
            parse_mode='Markdown'
        )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ ربات آماده‌ست...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
