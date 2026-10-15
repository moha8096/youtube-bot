import re
import json
import os
import subprocess
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ───────────────────────────────
TOKEN = os.environ.get("TOKEN")
COOKIES = "/app/cookies.txt"
DOWNLOAD_DIR = "/app/downloads"
DENO = "/root/.deno/bin/deno"
# ───────────────────────────────

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YOUTUBE_REGEX = re.compile(
    r'(https?://)?(www\.)?(m\.)?'
    r'(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+'
)

user_state = {}


def get_info(url: str) -> dict:
    cmd = [
        "yt-dlp",
        "--cookies", COOKIES,
        "--extractor-args", "youtube:player_client=tv_embedded",
        "--js-runtimes", f"deno:{DENO}",
        "--dump-json",
        "--no-playlist",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr.strip()[-500:])
    return json.loads(result.stdout)


def get_available_qualities(info: dict) -> list:
    seen = set()
    results = []

    for f in info.get('formats', []):
        vcodec = f.get('vcodec', 'none')
        height = f.get('height', 0)
        if vcodec == 'none': continue
        if not height: continue
        label = f"{height}p"
        if label in seen: continue
        seen.add(label)
        results.append({'q': label, 'height': height})

    results.sort(key=lambda x: x['height'], reverse=True)
    return results


def download_merge(url: str, height: int, out_path: str):
    fmt = (
        f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={height}]+bestaudio/"
        f"best[height<={height}]"
    )
    cmd = [
        "yt-dlp",
        "--cookies", COOKIES,
        "--extractor-args", "youtube:player_client=tv_embedded",
        "--js-runtimes", f"deno:{DENO}",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "-o", out_path,
        "--no-playlist",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr.strip()[-500:])


def upload_catbox(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        r = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": f},
            timeout=300
        )
    if r.status_code != 200 or not r.text.startswith("https://"):
        raise Exception(f"آپلود خطا داد: {r.text[:200]}")
    return r.text.strip()


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if user_id in user_state:
        state = user_state[user_id]
        selected = None

        for q in state['qualities']:
            if text == q['q']:
                selected = q
                break

        if not selected:
            lines = ["❌ کیفیت معتبر نیست. یکی از این‌ها رو بفرست:", ""]
            for q in state['qualities']:
                lines.append(f"• `{q['q']}`")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
            return

        del user_state[user_id]

        url = state['url']
        title = state['title']
        quality = selected['q']
        height = selected['height']

        msg = await update.message.reply_text(f"⏳ دارم دانلود و merge می‌کنم — {quality}...")

        try:
            safe_title = re.sub(r'[^\w\s-]', '', title)[:40]
            out_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}_{quality}.mp4")

            download_merge(url, height, out_path)

            size_mb = os.path.getsize(out_path) / 1024 / 1024
            await msg.edit_text(f"⏳ دارم آپلود می‌کنم به catbox — {size_mb:.1f} MB...")

            direct_link = upload_catbox(out_path)
            os.remove(out_path)

            await msg.edit_text(
                f"🎬 *{title}*\n"
                f"📐 کیفیت: `{quality}`\n"
                f"💾 حجم: `{size_mb:.1f} MB`\n\n"
                f"📥 [لینک مستقیم دانلود]({direct_link})\n\n"
                f"⚠️ لینک دائمیه.",
                parse_mode='Markdown',
                disable_web_page_preview=True
            )

        except Exception as e:
            await msg.edit_text(f"❌ خطا:\n`{str(e)[:400]}`", parse_mode='Markdown')
        return

    match = YOUTUBE_REGEX.search(text)
    if not match:
        await update.message.reply_text("❌ لینک یوتیوب معتبر نیست.")
        return

    url = match.group(0)
    if not url.startswith('http'):
        url = 'https://' + url

    msg = await update.message.reply_text("⏳ در حال پردازش...")

    try:
        info = get_info(url)
        title = info.get('title', 'بدون عنوان')
        duration = info.get('duration_string', '?')
        qualities = get_available_qualities(info)

        if not qualities:
            await msg.edit_text("❌ هیچ کیفیتی پیدا نشد.")
            return

        user_state[user_id] = {
            'url': url,
            'title': title,
            'qualities': qualities
        }

        lines = [
            f"🎬 *{title}*",
            f"⏱ مدت: `{duration}`",
            "",
            "📐 کیفیت مورد نظر رو بفرست:",
            ""
        ]
        for q in qualities:
            lines.append(f"• `{q['q']}`")

        await msg.edit_text("\n".join(lines), parse_mode='Markdown')

    except Exception as e:
        await msg.edit_text(f"❌ خطا:\n`{str(e)[:400]}`", parse_mode='Markdown')


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ ربات آماده‌ست...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
