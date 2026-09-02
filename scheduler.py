import csv
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from config import BASE_DIR, settings, logger
from gemini_generator import generate_content
from media_engine import create_image_card, generate_voiceover, create_vertical_video
from publisher import publish_post

CSV_FILE = BASE_DIR / "schedule.csv"
FIELDNAMES = [
    "id",
    "publish_time",
    "topic_title",
    "keywords_hashtags",
    "content_type",
    "platforms",
    "status",
    "error_log",
    "recurrence",
    "custom_caption",
    "language"
]


def init_csv():
    """Initializes schedule.csv with headers and sample records if it doesn't exist."""
    if not CSV_FILE.exists():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        sample_rows = [
            {
                "id": "101",
                "publish_time": now_str,
                "topic_title": "Garments Line Balancing Techniques & SAM Optimization",
                "keywords_hashtags": "#RMG #LineBalancing #Production #IndustrialEngineering",
                "content_type": "video",
                "platforms": "facebook,linkedin",
                "status": "pending",
                "error_log": "",
                "recurrence": "none",
                "custom_caption": "",
                "language": "en"
            },
            {
                "id": "102",
                "publish_time": now_str,
                "topic_title": "5S Implementation & Waste Reduction in Apparel Manufacturing",
                "keywords_hashtags": "#Lean #5S #Manufacturing #Efficiency",
                "content_type": "image",
                "platforms": "facebook,linkedin",
                "status": "pending",
                "error_log": "",
                "recurrence": "none",
                "custom_caption": "",
                "language": "en"
            },
            {
                "id": "103",
                "publish_time": now_str,
                "topic_title": "Smart Factory Automation & Real-Time Production Tracking",
                "keywords_hashtags": "#SmartFactory #Industry40 #Automation",
                "content_type": "text_only",
                "platforms": "facebook,linkedin",
                "status": "pending",
                "error_log": "",
                "recurrence": "none",
                "custom_caption": "",
                "language": "en"
            }
        ]
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(sample_rows)
        logger.info(f"schedule.csv তৈরি হয়েছে এবং {len(sample_rows)}টি নমুনা টাস্ক যুক্ত করা হয়েছে।")


def read_tasks() -> List[Dict[str, str]]:
    """Reads all rows from schedule.csv, providing defaults for missing columns."""
    if not CSV_FILE.exists():
        init_csv()
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            for field in FIELDNAMES:
                r.setdefault(field, "")
            if not r.get("language"):
                r["language"] = settings.DEFAULT_LANGUAGE
            rows.append(r)
        return rows


def write_tasks(rows: List[Dict[str, str]]):
    """Safely and atomically writes task rows to schedule.csv."""
    temp_dir = CSV_FILE.parent
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, newline="", encoding="utf-8") as tf:
        writer = csv.DictWriter(tf, fieldnames=FIELDNAMES)
        writer.writeheader()
        cleaned_rows = []
        for r in rows:
            clean_r = {k: r.get(k, "") for k in FIELDNAMES}
            if not clean_r.get("language"):
                clean_r["language"] = settings.DEFAULT_LANGUAGE
            cleaned_rows.append(clean_r)
        writer.writerows(cleaned_rows)
        temp_name = tf.name

    os.replace(temp_name, CSV_FILE)


def calculate_next_run(current_time_str: str, recurrence: str) -> str:
    """Calculates next publish_time based on recurrence pattern."""
    rec = recurrence.strip().lower()
    try:
        dt = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        dt = datetime.now()

    if rec == "daily":
        next_dt = dt + timedelta(days=1)
    elif rec == "weekly":
        next_dt = dt + timedelta(weeks=1)
    elif rec == "hourly":
        next_dt = dt + timedelta(hours=1)
    else:
        return ""
    return next_dt.strftime("%Y-%m-%d %H:%M")


def recover_stale_processing_tasks():
    """Recovers any tasks left stuck in 'processing' status on daemon startup or cycle."""
    if not CSV_FILE.exists():
        return
    rows = read_tasks()
    recovered = False
    for row in rows:
        if row.get("status", "").strip().lower() == "processing":
            row["status"] = "pending"
            row["error_log"] = "স্টেল প্রসেসিং টাস্ক স্বয়ংক্রিয়ভাবে পেন্ডিং অবস্থায় রিকভার করা হয়েছে।"
            recovered = True
            logger.info(f"🔄 [Task {row.get('id')}] স্টেল 'processing' অবস্থা থেকে 'pending'-এ রিকভার করা হয়েছে।")
    if recovered:
        write_tasks(rows)


def process_pending_tasks():
    """
    Checks schedule.csv against local time.
    Picks pending tasks whose publish_time has arrived,
    locks them to 'processing', triggers generation (or preserves custom text),
    renders media (reusing 1 asset across accounts), and publishes.
    """
    if not CSV_FILE.exists():
        init_csv()
        return

    # Recover any stale locks before picking
    recover_stale_processing_tasks()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = read_tasks()

    pending_tasks = [r for r in rows if r.get("status", "").strip().lower() == "pending" and r.get("publish_time", "").strip() <= now_str]
    if not pending_tasks:
        logger.info("ℹ️ কিউতে কোনো পেন্ডিং পোস্ট নেই। নতুন পোস্ট তাৎক্ষণিক তৈরি ও লাইভ পাবলিশ করতে 'python3 cli.py publish-now' ব্যবহার করুন।")
        return

    updated = False

    for row in rows:
        status = row.get("status", "").strip().lower()
        pub_time = row.get("publish_time", "").strip()

        if status == "pending" and pub_time <= now_str:
            task_id = row.get("id", "UNKNOWN")
            topic = row.get("topic_title", "")
            keywords = row.get("keywords_hashtags", "")
            content_type = row.get("content_type", "image").strip().lower()
            platforms = row.get("platforms", "facebook,linkedin")
            recurrence = row.get("recurrence", "none").strip().lower()
            custom_caption = row.get("custom_caption", "").strip()
            lang = row.get("language", settings.DEFAULT_LANGUAGE).strip().lower() or settings.DEFAULT_LANGUAGE

            # Lock row status to 'processing'
            row["status"] = "processing"
            write_tasks(rows)
            logger.info(f"⏳ [Task {task_id}] প্রসেসিং শুরু: {topic or 'কাস্টম পোস্ট'} ({content_type}, Lang={lang})")

            try:
                media_path = None
                caption_payload = None

                # EXACT USER TEXT PRESERVATION ROUTING
                if custom_caption:
                    logger.info(f"📝 [Task {task_id}] নির্দিষ্ট কাস্টম ক্যাপশন সংরক্ষিত হচ্ছে (Gemini জেনারেশন বাইপাস্ড)।")
                    caption_payload = custom_caption

                    if content_type == "image":
                        lines = [l.strip() for l in custom_caption.splitlines() if l.strip() and not l.startswith("#")]
                        badge = "Custom Post" if lang == "en" else "কাস্টম পোস্ট"
                        default_bullets = ["Key Insight", "Action Plan", "Results"] if lang == "en" else ["মূল আলোচনা", "বাস্তবায়ন", "ফলাফল"]
                        bullets = lines[1:4] if len(lines) >= 4 else (lines[:3] if lines else default_bullets)
                        card_title = topic if topic else (lines[0][:40] if lines else "Custom Post")
                        media_path = create_image_card(card_title, badge, bullets, f"card_{task_id}.png", lang=lang)

                    elif content_type == "video":
                        voiceover_text = custom_caption
                        audio_path = generate_voiceover(voiceover_text, f"voice_{task_id}.mp3", lang=lang)
                        lines = [l.strip() for l in custom_caption.splitlines() if l.strip() and not l.startswith("#")]
                        default_slides = ["Introduction", "Core Points", "Summary"] if lang == "en" else ["ভূমিকা", "মূল আলোচনা", "সারসংক্ষেপ"]
                        slides = lines[:3] if len(lines) >= 3 else default_slides
                        video_title = topic if topic else (lines[0][:40] if lines else "Custom Post")
                        media_path = create_vertical_video(video_title, slides, audio_path, f"video_{task_id}.mp4", lang=lang)

                else:
                    # Standard Keyword/Topic -> AI Content Generation in Selected Language
                    content = generate_content(topic, keywords, content_type, lang=lang)
                    caption_payload = content.get("platform_captions") or content.get("caption", f"{topic}\n\n{keywords}")

                    if content_type == "image":
                        badge = content.get("badge", "Guide" if lang == "en" else "গাইড")
                        default_bullets = ["Efficiency Gain", "Waste Reduction", "Quality Control"] if lang == "en" else ["দক্ষতা বৃদ্ধি", "অপচয় হ্রাস", "সঠিক পর্যবেক্ষণ"]
                        bullets = content.get("bullets", default_bullets)
                        media_path = create_image_card(topic, badge, bullets, f"card_{task_id}.png", lang=lang)

                    elif content_type == "video":
                        default_voice = f"Today we discuss {topic} in detail." if lang == "en" else f"{topic} নিয়ে আজকের আলোচনা।"
                        voiceover_text = content.get("voiceover", default_voice)
                        audio_path = generate_voiceover(voiceover_text, f"voice_{task_id}.mp3", lang=lang)
                        default_slides = ["Overview", "Key Steps", "Outcomes"] if lang == "en" else ["ভূমিকা", "মূল পয়েন্ট", "ফলাফল"]
                        slides = content.get("slides", default_slides)
                        media_path = create_vertical_video(topic, slides, audio_path, f"video_{task_id}.mp4", lang=lang)

                # 3. Publish or Dry-Run Dump (Reusing single media_path across all accounts)
                is_live, pub_message, per_account_results = publish_post(
                    task_id=task_id,
                    content_type=content_type,
                    caption=caption_payload,
                    media_path=media_path,
                    platforms=platforms
                )

                exec_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Build readable per-platform log summary
                account_summaries = []
                for p_key, p_res in per_account_results.items():
                    p_status = p_res.get("status", "unknown")
                    if p_status == "posted":
                        account_summaries.append(f"[{p_key}: posted ({p_res.get('post_url', 'OK')})]")
                    elif p_status == "skipped":
                        account_summaries.append(f"[{p_key}: skipped ({p_res.get('reason', 'OFF')})]")
                    elif p_status == "failed":
                        account_summaries.append(f"[{p_key}: failed ({p_res.get('error', 'Error')})]")
                    elif p_status == "dry_run":
                        account_summaries.append(f"[{p_key}: dry_run ({p_res.get('folder', 'saved')})]")

                detailed_log = " ".join(account_summaries)

                # RECURRING SCHEDULE SUPPORT
                if recurrence in ["daily", "weekly", "hourly"]:
                    next_time = calculate_next_run(pub_time, recurrence)
                    row["publish_time"] = next_time
                    row["status"] = "pending"
                    status_prefix = "পাবলিশ সম্পন্ন" if is_live else "ড্রাফট তৈরি সম্পন্ন"
                    row["error_log"] = f"{status_prefix}: {detailed_log} ({exec_time}) | পরবর্তী শিডিউল: {next_time}"
                    logger.info(f"🔁 [Task {task_id}] রিকারিং টাস্ক পরবর্তী শিডিউলে সেট করা হয়েছে: {next_time}")
                else:
                    if is_live:
                        row["status"] = "posted"
                        row["error_log"] = f"পাবলিশ সম্পন্ন: {detailed_log} ({exec_time})"
                    else:
                        row["status"] = "posted (dry-run)"
                        row["error_log"] = f"ড্রাফট তৈরি সম্পন্ন: {detailed_log} ({exec_time})"

                logger.info(f"🎉 [Task {task_id}] সফলভাবে সম্পন্ন হয়েছে ({row['status']})")

            except Exception as e:
                logger.error(f"❌ [Task {task_id}] প্রক্রিয়াকরণ ব্যর্থ: {e}", exc_info=True)
                row["status"] = "failed"
                row["error_log"] = f"Error: {str(e)}"

            updated = True

    if updated:
        write_tasks(rows)
