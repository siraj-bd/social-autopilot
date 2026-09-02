import sys
import time
import argparse
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from config import settings, logger
from scheduler import init_csv, process_pending_tasks, read_tasks, write_tasks, recover_stale_processing_tasks
from gemini_generator import generate_content
from media_engine import create_image_card, generate_voiceover, create_vertical_video
from publisher import publish_post


def run_daemon(interval_seconds: int = 60):
    """Starts the APScheduler background daemon to monitor schedule.csv."""
    init_csv()
    recover_stale_processing_tasks()
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_pending_tasks, 'interval', seconds=interval_seconds)
    scheduler.start()
    logger.info(f"🚀 Social Autopilot ডেমন চালু হয়েছে (প্রতি {interval_seconds} সেকেন্ডে শিডিউল চেক করবে)...")
    logger.info("Ctrl+C চেপে ডেমন বন্ধ করতে পারেন।")
    try:
        # Run first check immediately on start
        process_pending_tasks()
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("🛑 Social Autopilot ডেমন বন্ধ করা হয়েছে।")


def test_dry_run(content_type: str = "image", lang: str = "en"):
    """Runs a manual dry-run generation for testing without modifying schedule.csv."""
    valid_types = ["image", "video", "text_only"]
    if content_type not in valid_types:
        print(f"ত্রুটি: ফরম্যাট অবশ্যই {valid_types} এর একটি হতে হবে।")
        sys.exit(1)

    logger.info(f"🧪 টেস্ট ড্রাফট রান শুরু হচ্ছে: ফরম্যাট={content_type}, Lang={lang}")
    persona = settings.PROFILE_TYPE
    if lang == "bn":
        if persona == "company":
            topic = "পোশাক শিল্পে আধুনিক সুইং টেকনোলজি ও কোয়ালিটি কন্ট্রোল"
            keywords = "#ApparelSewingProcess #GarmentTechnology #QualityControl #RMGIndustry"
        else:
            topic = "পোশাক শিল্পে লীন ম্যানুফ্যাকচারিং ও 5S বাস্তবায়ন"
            keywords = "#ApparelManufacturing #IndustrialEngineering #LineBalancing #SAM #LeanManufacturing"
    else:
        if persona == "company":
            topic = "Modern Sewing Technology & Quality Control Standards in Apparel"
            keywords = "#ApparelSewingProcess #GarmentTechnology #QualityControl #RMGIndustry"
        else:
            topic = "Mathematical Line Balancing & Efficiency Optimization in RMG Lines"
            keywords = "#ApparelManufacturing #IndustrialEngineering #LineBalancing #SAM #LeanManufacturing"

    content = generate_content(topic, keywords, content_type, lang=lang)
    media_path = None

    if content_type == "image":
        badge = content.get("badge", "Guide" if lang == "en" else "গাইড")
        default_bullets = ["Efficiency Gain", "Waste Reduction", "Quality Control"] if lang == "en" else ["কর্মক্ষমতা বৃদ্ধি", "অপচয় হ্রাস", "সঠিক পর্যবেক্ষণ"]
        media_path = create_image_card(
            title=topic,
            badge=badge,
            bullets=content.get("bullets", default_bullets),
            filename="test_run_card.png",
            lang=lang
        )
    elif content_type == "video":
        default_voice = f"Analyzing {topic} in detail." if lang == "en" else f"{topic} বিষয়ে বিস্তারিত আলোচনা।"
        audio = generate_voiceover(
            content.get("voiceover", default_voice),
            filename="test_run_voice.mp3",
            lang=lang
        )
        default_slides = ["Overview & Context", "Core Analysis", "Key Takeaways"] if lang == "en" else ["ভূমিকা ও প্রেক্ষাপট", "মূল সমস্যা ও সমাধান", "ভবিষ্যত করণীয়"]
        media_path = create_vertical_video(
            title=topic,
            slides=content.get("slides", default_slides),
            audio_path=audio,
            filename="test_run_short.mp4",
            lang=lang
        )

    is_live, msg, _ = publish_post(
        task_id="TEST_RUN",
        content_type=content_type,
        caption=content.get("platform_captions") or content.get("caption", ""),
        media_path=media_path,
        platforms="facebook,linkedin",
        dry_run=True
    )

    logger.info(f"✅ টেস্ট রান সম্পন্ন হয়েছে: {msg}")


def publish_now(
    topic: Optional[str] = None,
    content_type: str = "text_only",
    keywords: Optional[str] = None,
    platforms: str = "linkedin",
    caption: Optional[str] = None,
    lang: str = "en"
):
    """
    Instantly publishes content to configured platforms (e.g. LinkedIn, Facebook).
    If custom caption is passed, preserves exact text and bypasses AI rewriting.
    Defaults to English, supports optional Bengali mode.
    """
    persona = settings.PROFILE_TYPE
    print("\n" + "=" * 70)
    print("🚀 [Publish-Now] লাইভ পাবলিশিং শুরু হচ্ছে...")
    print(f"👤 সক্রিয় পার্সোনা : {persona.upper()} ({settings.LINKEDIN_AUTHOR_URN})")
    print(f"🌐 নির্বাচিত ভাষা   : {lang.upper()} (Default: EN)")
    if caption:
        print(f"📝 নির্দিষ্ট টেক্সট : কাস্টম ক্যাপশন বজায় রাখা হচ্ছে (Gemini বাইপাস্ড)")
    else:
        print(f"📌 পোস্টের বিষয়   : {topic or 'স্বয়ংক্রিয় পার্সোনা বিষয়'}")
    print(f"📐 কনটেন্ট ফরম্যাট: {content_type.upper()} | প্ল্যাটফর্ম: {platforms}")
    print("=" * 70 + "\n")

    media_path = None
    caption_payload = None
    task_id = f"LIVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # EXACT USER TEXT PRESERVATION
    if caption:
        final_caption = caption.strip()
        caption_payload = final_caption
        logger.info("📝 নির্দিষ্ট কাস্টম ক্যাপশন বজায় রেখে পোস্ট করা হচ্ছে (Gemini জেনারেশন বাইপাস্ড)।")

        if content_type == "image":
            lines = [l.strip() for l in final_caption.splitlines() if l.strip() and not l.startswith("#")]
            badge = "Custom Post" if lang == "en" else "কাস্টম পোস্ট"
            default_bullets = ["Key Insight", "Action Plan", "Results"] if lang == "en" else ["মূল আলোচনা", "বাস্তবায়ন", "ফলাফল"]
            bullets = lines[1:4] if len(lines) >= 4 else (lines[:3] if lines else default_bullets)
            card_title = topic if topic else (lines[0][:40] if lines else "Custom Post")
            media_path = create_image_card(card_title, badge, bullets, f"live_{task_id}.png", lang=lang)

        elif content_type == "video":
            voiceover_text = final_caption
            audio_path = generate_voiceover(voiceover_text, f"live_voice_{task_id}.mp3", lang=lang)
            lines = [l.strip() for l in final_caption.splitlines() if l.strip() and not l.startswith("#")]
            default_slides = ["Introduction", "Core Points", "Summary"] if lang == "en" else ["ভূমিকা", "মূল আলোচনা", "সারসংক্ষেপ"]
            slides = lines[:3] if len(lines) >= 3 else default_slides
            video_title = topic if topic else (lines[0][:40] if lines else "Custom Post")
            media_path = create_vertical_video(video_title, slides, audio_path, f"live_video_{task_id}.mp4", lang=lang)

    else:
        # Standard Keyword/Topic -> AI Content Generation
        if not topic:
            if lang == "bn":
                if persona == "company":
                    topic = "গার্মেন্টস সুইং প্রসেস ও কোয়ালিটি কন্ট্রোল স্ট্যান্ডার্ড"
                    default_kw = "#ApparelSewingProcess #GarmentTechnology #QualityControl #SewingMethods"
                else:
                    topic = "গার্মেন্টস লাইনে ম্যাথমেটিক্যাল ব্যালেন্সিং ও এফিসিয়েন্সি অপটিমাইজেশন"
                    default_kw = "#ApparelManufacturing #IndustrialEngineering #LineBalancing #SAM #LeanManufacturing"
            else:
                if persona == "company":
                    topic = "Garment Sewing Process & Quality Control Standards"
                    default_kw = "#ApparelSewingProcess #GarmentTechnology #QualityControl #SewingMethods"
                else:
                    topic = "Mathematical Line Balancing & Efficiency Optimization in Apparel"
                    default_kw = "#ApparelManufacturing #IndustrialEngineering #LineBalancing #SAM #LeanManufacturing"
            keywords = keywords or default_kw
        else:
            keywords = keywords or "#Automation #ApparelIndustry"

        logger.info(f"কনটেন্ট জেনারেশন শুরু: {topic} ({content_type}, Lang={lang})")
        content = generate_content(topic, keywords, content_type, lang=lang)
        caption_payload = content.get("platform_captions") or content.get("caption", f"{topic}\n\n{keywords}")

        if content_type == "image":
            badge = content.get("badge", "Guide" if lang == "en" else "গাইড")
            default_bullets = ["Efficiency Gain", "Waste Reduction", "Quality Control"] if lang == "en" else ["দক্ষতা বৃদ্ধি", "অপচয় হ্রাস", "মান নিয়ন্ত্রণ"]
            bullets = content.get("bullets", default_bullets)
            media_path = create_image_card(topic, badge, bullets, f"live_{task_id}.png", lang=lang)
        elif content_type == "video":
            default_voice = f"Analyzing {topic}." if lang == "en" else f"{topic} নিয়ে আজকের বিশেষ আলোচনা।"
            voiceover_text = content.get("voiceover", default_voice)
            audio_path = generate_voiceover(voiceover_text, f"live_voice_{task_id}.mp3", lang=lang)
            default_slides = ["Overview", "Key Findings", "Action Points"] if lang == "en" else ["ভূমিকা ও প্রেক্ষাপট", "মূল আলোচনা", "ফলাফল"]
            slides = content.get("slides", default_slides)
            media_path = create_vertical_video(topic, slides, audio_path, f"live_video_{task_id}.mp4", lang=lang)

    # Live Publish (dry_run=False)
    is_live, pub_message, per_account_results = publish_post(
        task_id=task_id,
        content_type=content_type,
        caption=caption_payload,
        media_path=media_path,
        platforms=platforms,
        dry_run=False
    )

    print("\n" + "-" * 70)
    if is_live:
        print(f"🎉 পোস্ট সফলভাবে লাইভ পাবলিশ হয়েছে!")
        print(f"👉 প্ল্যাটফর্ম স্ট্যাটাস: {pub_message}")
    else:
        print(f"⚠️ লাইভ পাবলিশ সম্পন্ন হয়নি ({pub_message})।")
        print("💡 ড্রাফট ফাইলগুলো 'output/' ফোল্ডারে সংরক্ষিত হয়েছে।")
    print("-" * 70 + "\n")


def list_tasks():
    """Prints all scheduled tasks in a clean terminal table."""
    tasks = read_tasks()
    if not tasks:
        print("কোনো টাস্ক পাওয়া যায়নি।")
        return

    header = f"{'ID':<5} | {'Publish Time':<17} | {'Type':<10} | {'Lang':<5} | {'Recurrence':<10} | {'Status':<18} | {'Topic / Caption':<30}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for t in tasks:
        display_text = t.get('custom_caption', '').replace('\n', ' ') if t.get('custom_caption') else t.get('topic_title', '')
        print(f"{t.get('id', ''):<5} | {t.get('publish_time', ''):<17} | {t.get('content_type', ''):<10} | {t.get('language', 'en'):<5} | {t.get('recurrence', 'none'):<10} | {t.get('status', ''):<18} | {display_text[:28]:<30}")
    print("-" * len(header))


def add_task(
    topic: str,
    content_type: str,
    publish_time: str,
    keywords: str,
    platforms: str,
    caption: str = "",
    recurrence: str = "none",
    lang: str = "en"
):
    """Appends a new task row to schedule.csv with optional custom caption, recurrence, and language."""
    tasks = read_tasks()
    next_id = str(max([int(t.get("id", 0)) for t in tasks if t.get("id", "").isdigit()] + [100]) + 1)

    new_row = {
        "id": next_id,
        "publish_time": publish_time,
        "topic_title": topic,
        "keywords_hashtags": keywords,
        "content_type": content_type,
        "platforms": platforms,
        "status": "pending",
        "error_log": "",
        "recurrence": recurrence,
        "custom_caption": caption,
        "language": lang
    }
    tasks.append(new_row)
    write_tasks(tasks)
    rec_info = f" [Recurrence: {recurrence}]" if recurrence != "none" else ""
    cap_info = " [Custom Caption]" if caption else ""
    logger.info(f"✅ নতুন টাস্ক যোগ করা হয়েছে: ID={next_id}, Topic='{topic}', Time={publish_time}, Lang={lang}{rec_info}{cap_info}")


def main():
    parser = argparse.ArgumentParser(description="Social Autopilot CLI Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="উপলব্ধ কমান্ডসমূহ")

    # Command: run
    run_parser = subparsers.add_parser("run", help="শিডিউলার ডেমন চালু করুন")
    run_parser.add_argument("--interval", type=int, default=60, help="শিডিউল চেক ইন্টারভাল (সেকেন্ড)")

    # Command: publish-now / generate-and-publish
    pub_parser = subparsers.add_parser("publish-now", aliases=["generate-and-publish"], help="তাৎক্ষণিকভাবে কনটেন্ট তৈরি বা কাস্টম টেক্সট দিয়ে সরাসরি লাইভ পাবলিশ করুন")
    pub_parser.add_argument("--title", help="পোস্টের বিষয় / শিরোনাম (না দিলে স্বয়ংক্রিয়ভাবে পার্সোনা অনুযায়ী নির্বাচিত হবে)")
    pub_parser.add_argument("--caption", help="ব্যবহারকারীর সম্পূর্ণ নির্দিষ্ট কাস্টম ক্যাপশন (Gemini জেনারেশন বাইপাস করবে)")
    pub_parser.add_argument("--type", choices=["video", "image", "text_only"], default="text_only", help="কনটেন্ট ফরম্যাট (default: text_only)")
    pub_parser.add_argument("--lang", choices=["en", "bn"], default="en", help="কনটেন্ট ভাষা (default: en)")
    pub_parser.add_argument("--keywords", help="হ্যাশট্যাগ / কিওয়ার্ড")
    pub_parser.add_argument("--platforms", default="linkedin", help="টার্গেট প্ল্যাটফর্ম (default: linkedin)")

    # Command: test-dry-run
    test_parser = subparsers.add_parser("test-dry-run", help="টেস্ট রান ও ড্রাফট ফাইল তৈরি")
    test_parser.add_argument("type", nargs="?", default="image", choices=["image", "video", "text_only"], help="কনটেন্ট ফরম্যাট")
    test_parser.add_argument("--lang", choices=["en", "bn"], default="en", help="ভাষা (default: en)")

    # Command: process-now
    subparsers.add_parser("process-now", help="এখনই পেন্ডিং টাস্ক প্রসেস করুন")

    # Command: list
    subparsers.add_parser("list", help="শিডিউলকৃত সকল টাস্কের তালিকা দেখুন")

    # Command: add
    add_parser = subparsers.add_parser("add", help="নতুন টাস্ক যোগ করুন")
    add_parser.add_argument("--title", default="", help="পোস্টের বিষয় / শিরোনাম")
    add_parser.add_argument("--caption", default="", help="সম্পূর্ণ নির্দিষ্ট কাস্টম ক্যাপশন (থাকলে Gemini বাইপাস হবে)")
    add_parser.add_argument("--type", choices=["video", "image", "text_only"], default="image", help="ফরম্যাট")
    add_parser.add_argument("--lang", choices=["en", "bn"], default="en", help="ভাষা (default: en)")
    add_parser.add_argument("--time", default=datetime.now().strftime("%Y-%m-%d %H:%M"), help="পাবলিশ টাইম (YYYY-MM-DD HH:MM)")
    add_parser.add_argument("--recurrence", choices=["none", "daily", "weekly", "hourly"], default="none", help="রিকারিং শিডিউল (none, daily, weekly, hourly)")
    add_parser.add_argument("--keywords", default="#Automation #Technology", help="হ্যাশট্যাগ / কিওয়ার্ড")
    add_parser.add_argument("--platforms", default="facebook,linkedin", help="টার্গেট প্ল্যাটফর্ম")

    args = parser.parse_args()

    if args.command == "run":
        run_daemon(args.interval)
    elif args.command in ["publish-now", "generate-and-publish"]:
        publish_now(args.title, args.type, args.keywords, args.platforms, args.caption, args.lang)
    elif args.command == "test-dry-run":
        test_dry_run(args.type, args.lang)
    elif args.command == "process-now":
        process_pending_tasks()
    elif args.command == "list":
        list_tasks()
    elif args.command == "add":
        add_task(args.title, args.type, args.time, args.keywords, args.platforms, args.caption, args.recurrence, args.lang)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
