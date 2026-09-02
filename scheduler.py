import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from config import BASE_DIR, logger
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
    "error_log"
]


def init_csv():
    """Initializes schedule.csv with headers and sample records if it doesn't exist."""
    if not CSV_FILE.exists():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        sample_rows = [
            {
                "id": "101",
                "publish_time": now_str,
                "topic_title": "গার্মেন্টস লাইনে ব্যালেন্সিং টেকনিক",
                "keywords_hashtags": "#RMG #LineBalancing #Production #Apparel",
                "content_type": "video",
                "platforms": "facebook,linkedin",
                "status": "pending",
                "error_log": ""
            },
            {
                "id": "102",
                "publish_time": now_str,
                "topic_title": "পোশাক শিল্পে 5S বাস্তবায়ন ও সুবিধা",
                "keywords_hashtags": "#Lean #5S #Manufacturing #Efficiency",
                "content_type": "image",
                "platforms": "facebook,linkedin",
                "status": "pending",
                "error_log": ""
            },
            {
                "id": "103",
                "publish_time": now_str,
                "topic_title": "স্মার্ট ফ্যাক্টরি ও অটোমেশনের প্রয়োজনীয়তা",
                "keywords_hashtags": "#SmartFactory #Industry40 #Automation",
                "content_type": "text_only",
                "platforms": "facebook,linkedin",
                "status": "pending",
                "error_log": ""
            }
        ]
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(sample_rows)
        logger.info(f"schedule.csv তৈরি হয়েছে এবং {len(sample_rows)}টি নমুনা টাস্ক যুক্ত করা হয়েছে।")


def read_tasks() -> List[Dict[str, str]]:
    """Reads all rows from schedule.csv."""
    if not CSV_FILE.exists():
        init_csv()
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_tasks(rows: List[Dict[str, str]]):
    """Safely and atomically writes task rows to schedule.csv."""
    temp_dir = CSV_FILE.parent
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, newline="", encoding="utf-8") as tf:
        writer = csv.DictWriter(tf, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
        temp_name = tf.name

    os.replace(temp_name, CSV_FILE)


def process_pending_tasks():
    """
    Checks schedule.csv against local time.
    Picks pending tasks whose publish_time has arrived,
    locks them to 'processing', triggers generation, renders media,
    and publishes (or dumps to dry-run).
    """
    if not CSV_FILE.exists():
        init_csv()
        return

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

            # Lock row status to 'processing'
            row["status"] = "processing"
            write_tasks(rows)
            logger.info(f"⏳ [Task {task_id}] প্রসেসিং শুরু: {topic} ({content_type})")

            try:
                # 1. AI Content Generation
                content = generate_content(topic, keywords, content_type)
                caption = content.get("caption", f"{topic}\n\n{keywords}")
                media_path = None

                # 2. Free Local Media Generation
                if content_type == "image":
                    badge = content.get("badge", "গাইড")
                    bullets = content.get("bullets", ["দক্ষতা বৃদ্ধি", "অপচয় হ্রাস", "সঠিক পর্যবেক্ষণ"])
                    media_path = create_image_card(topic, badge, bullets, f"card_{task_id}.png")

                elif content_type == "video":
                    voiceover_text = content.get("voiceover", f"{topic} নিয়ে আজকের আলোচনা।")
                    audio_path = generate_voiceover(voiceover_text, f"voice_{task_id}.mp3")
                    slides = content.get("slides", ["ভূমিকা", "মূল পয়েন্ট", "ফলাফল"])
                    media_path = create_vertical_video(topic, slides, audio_path, f"video_{task_id}.mp4")

                # 3. Publish or Dry-Run Dump
                is_live, pub_message = publish_post(
                    task_id=task_id,
                    content_type=content_type,
                    caption=caption,
                    media_path=media_path,
                    platforms=platforms
                )

                exec_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if is_live:
                    row["status"] = "posted"
                    row["error_log"] = f"পাবলিশ সম্পন্ন: {pub_message} ({exec_time})"
                else:
                    row["status"] = "posted (dry-run)"
                    row["error_log"] = f"ড্রাফট তৈরি সম্পন্ন: {pub_message} ({exec_time})"

                logger.info(f"🎉 [Task {task_id}] সফলভাবে সম্পন্ন হয়েছে ({row['status']})")

            except Exception as e:
                logger.error(f"❌ [Task {task_id}] প্রক্রিয়াকরণ ব্যর্থ: {e}", exc_info=True)
                row["status"] = "failed"
                row["error_log"] = f"Error: {str(e)}"

            updated = True

    if updated:
        write_tasks(rows)
