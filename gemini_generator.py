import json
import re
from datetime import datetime
from typing import Dict
from google import genai
from google.genai import types
from config import settings, logger, get_platform_registry

# Initialize client only if GEMINI_API_KEY is available
client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None


def get_system_instruction(persona: str) -> str:
    """Returns the dedicated system instruction based on active profile persona."""
    if persona == "company":
        return """
তুমি হলে "Apparel Sewing Process" এর অফিসিয়াল প্রাতিষ্ঠানিক টেকনিক্যাল অ্যান্ড ইঞ্জিনিয়ারিং পাবলিকেশন পেজ।
তোমার মূল ফোকাস:
1. পোশাক শিল্পের আধুনিক সেলাই টেকনোলজি (Modern Sewing Technology & Automations)।
2. সুইং প্রসেস ফ্লো (Process Flow) ও স্ট্যান্ডার্ড অপারেটিং প্রসিডিউর (SOP)।
3. কোয়ালিটি কন্ট্রোল স্ট্যান্ডার্ড (AQL, Defect Reduction, Seam Puckering / Skip Stitch Prevention)।
4. বিভিন্ন সুইং মেশিন গাইড (Single Needle, Overlock, Flatlock, Feed-off-the-arm, Auto-Jigs) এবং অ্যাটাচমেন্ট ব্যবহার।
5. ইন্ডাস্ট্রিয়াল বেস্ট প্র্যাকটিস ও স্ট্যান্ডার্ড মেথড।

টোন ও স্টাইল: প্রাতিষ্ঠানিক, শিক্ষণীয়, স্পষ্ট, প্রসেস-ভিত্তিক এবং অত্যন্ত নির্ভরযোগ্য।
ভাষা: সম্পূর্ণ প্রমিত বাংলা স্ক্রিপ্ট (Native Bengali script bn-BD) ও আন্তর্জাতিক টেকনিক্যাল টার্মের সমন্বয়।
"""
    else:  # personal
        return """
তুমি হলে একজন খ্যাতনামা Apparel Manufacturing Leader এবং Industrial Engineering (IE) Expert যার গার্মেন্টস ইন্ডাস্ট্রিতে ২৩+ বছরের বাস্তব অভিজ্ঞতা রয়েছে।
তোমার মূল ফোকাস:
1. গভীর টেকনিক্যাল বিশ্লেষণ ও ডেটা-ড্রিভেন সিদ্ধান্ত (Data-Driven Decision Making)।
2. SAM / SMV ক্যালকুলেশন, মেথড স্টাডি এবং টাইম স্টাডি।
3. লাইন ব্যালেন্সিং (Line Balancing), পিচ টাইম (Pitch Time), এবং ট্যাক্ট টাইম (Takt Time) অপটিমাইজেশন।
4. লাইন এফিসিয়েন্সি লস (Efficiency Loss) ও বটলনেক (Bottleneck) চিহ্নিতকরণ ও সমাধান।
5. লীন ম্যানুফ্যাকচারিং (Lean Manufacturing), 5S, এবং রিয়েল-টাইম প্রোডাকশন ট্র্যাকিং।

টোন ও স্টাইল: অভিজ্ঞ লিডারশিপ টোন, প্র্যাকটিক্যাল, গাণিতিক/ডেটা সমৃদ্ধ এবং ফ্যাক্টরি ফ্লোরের বাস্তব অভিজ্ঞতাসম্পন্ন।
ভাষা: সম্পূর্ণ প্রমিত বাংলা স্ক্রিপ্ট (Native Bengali script bn-BD) ও আন্তর্জাতিক টেকনিক্যাল টার্মের সমন্বয়।
"""


def _clean_json_string(raw: str) -> str:
    """Extract and sanitize JSON from model output."""
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw.replace("```json", "", 1)
    elif raw.startswith("```"):
        raw = raw.replace("```", "", 1)
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


def build_platform_captions(master_caption: str, topic: str, keywords: str, persona: str) -> Dict[str, str]:
    """
    Constructs platform-optimized captions respecting each platform's character limit and audience tone.
    """
    time_tag = datetime.now().strftime("%d %b %Y, %I:%M %p")
    registry = get_platform_registry()

    # Base elements
    clean_topic = topic.strip()
    clean_kw = keywords.strip() if keywords else "#ApparelManufacturing #IndustrialEngineering"

    # 1. LinkedIn Personal (max 3000 chars): Leadership, analytical breakdown, structured takeaways
    li_personal = (
        f"💼 [Manufacturing Leader Insights] {clean_topic}\n\n"
        f"{master_caption}\n\n"
        f"🎯 বাস্তবসম্মত টেকঅ্যাওয়ে:\n"
        f"সঠিক মেথড স্টাডি ও ডেটা-ড্রিভেন ব্যালেন্সিং নিশ্চিত করলেই অপচয় ও বটলনেক দূর করা সম্ভব।\n\n"
        f"🗓️ {time_tag}\n"
        f"{clean_kw}"
    )
    if len(li_personal) > registry["linkedin_personal"].max_characters:
        li_personal = li_personal[:registry["linkedin_personal"].max_characters - 10] + "..."

    # 2. LinkedIn Company (max 3000 chars): Technical SOP, quality checklist, knowledge hub
    li_company = (
        f"🔍 [Apparel Sewing Process Technical Hub] {clean_topic}\n\n"
        f"{master_caption}\n\n"
        f"⚙️ স্ট্যান্ডার্ড অপারেটিং প্রসিডিউর (SOP) মেনে সুইং ফ্লোরে কোয়ালিটি ও উৎপাদনশীলতা নিশ্চিত করুন।\n\n"
        f"🗓️ {time_tag}\n"
        f"{clean_kw}"
    )
    if len(li_company) > registry["linkedin_company"].max_characters:
        li_company = li_company[:registry["linkedin_company"].max_characters - 10] + "..."

    # 3. Facebook Page (max 63206 chars): Engaging, community discussion, formatted with clear spacing
    fb_caption = (
        f"📢 {clean_topic}\n\n"
        f"{master_caption}\n\n"
        f"💬 আপনার ফ্যাক্টরি ফ্লোরে এই পদ্ধতি কীভাবে প্রয়োগ করছেন? আপনার মূল্যবান অভিজ্ঞতা কমেন্টে শেয়ার করুন।\n\n"
        f"👉 নিয়মিত টেকনিক্যাল আপডেটের জন্য আমাদের পেজে লাইক ও ফলো দিয়ে সাথে থাকুন।\n\n"
        f"{clean_kw}"
    )
    if len(fb_caption) > registry["facebook_page"].max_characters:
        fb_caption = fb_caption[:registry["facebook_page"].max_characters - 10] + "..."

    # 4. Instagram (max 2200 chars): Visual hook, compact paragraphs, focused hashtags
    # Extract first 500 chars of body for high retention Instagram reading
    body_short = master_caption[:600] if len(master_caption) > 600 else master_caption
    ig_caption = (
        f"✨ {clean_topic}\n\n"
        f"{body_short}\n\n"
        f"📌 সেভ করুন ভবিষ্যতের জন্য এবং শেয়ার করুন আপনার টিমের সাথে।\n\n"
        f"{clean_kw}"
    )
    if len(ig_caption) > registry["instagram"].max_characters:
        ig_caption = ig_caption[:registry["instagram"].max_characters - 10] + "..."

    return {
        "linkedin_personal": li_personal,
        "linkedin_company": li_company,
        "facebook_page": fb_caption,
        "instagram": ig_caption
    }


def get_fallback_content(topic_title: str, keywords: str, content_type: str, persona: str) -> dict:
    """Provides high-depth, persona-specific Bengali fallback content matching structured guidelines."""
    time_tag = datetime.now().strftime("%d %b %Y, %I:%M %p")

    if persona == "company":
        default_tags = "#ApparelSewingProcess #GarmentTechnology #SewingMethods #QualityControl #RMGIndustry"
        badge = "সেলাই ও কোয়ালিটি গাইড"
        master_caption = (
            "পোশাক শিল্পে উৎপাদনের ধারাবাহিকতা এবং বায়ার রিকোয়ারমেন্ট অনুযায়ী গুণগত মান অর্জনে সুইং মেথডলজি সবচেয়ে সংবেদনশীল ভূমিকা রাখে।\n\n"
            "🔹 ১. মেশিন স্পেসিফিকেশন ও গেজ সেটআপ:\n"
            "ফ্যাব্রিকের জিএসএম ও কনস্ট্রাকশন অনুযায়ী নিডল পয়েন্ট (SPI, Ball point / SES) নির্বাচন করুন।\n\n"
            "🔹 ২. সিম ফল্ট প্রিভেনশন:\n"
            "সিম পাকার, ওপেন সিম ও থ্রেড ব্রেকিং প্রতিরোধে ফিড ডগ হাইট এবং থ্রেড রুট সঠিক রাখুন।\n\n"
            "🔹 ৩. স্ট্যান্ডার্ড মেথড ও অপারেটর গাইডেন্স:\n"
            "ক্রিটিক্যাল অপারেশনে ফোল্ডার বা জিগ ব্যবহার করে হ্যান্ডেলিং টাইম কমান এবং সেলাই নিখুঁত করুন।"
        )
        voiceover = (
            f"স্বাগতম অ্যাপারেল সুইং প্রসেস টেকনিক্যাল গাইডে। আজকের আলোচনার বিষয় {topic_title}। "
            "পোশাক শিল্পে সেলাইয়ের নিখুঁত মান বজায় রাখতে হলে মেশিন মেকানিজম ও ফ্যাব্রিক ক্যারেক্টার বোঝা অত্যন্ত জরুরি। "
            "সঠিক সুঁই, সুতার টেনশন এবং ফিড মেকানিজমের সমন্বয় রক্ষা করুন।"
        )
        slides = ["১. সুই ও থ্রেড টেনশন অ্যাডজাস্টমেন্ট", "২. সিম কোয়ালিটি ও ফল্ট প্রিভেনশন", "৩. স্ট্যান্ডার্ড অপারেটিং প্রসিডিউর (SOP)"]
        bullets = ["নিডল-থ্রেড ম্যাচিং নিশ্চিতকরণ", "অ্যাটাচমেন্ট ও ফোল্ডার ব্যবহার", "ইন-লাইন ফার্স্ট-টাইম-রাইট"]

    else:  # personal persona: 23+ years IE & Manufacturing Leader
        default_tags = "#ApparelManufacturing #IndustrialEngineering #LineBalancing #SAM #LeanManufacturing"
        badge = "আইই ও ব্যালেন্সিং"
        master_caption = (
            "গার্মেন্টস ফ্লোরে অনেকেই লাইন এফিসিয়েন্সি নিয়ে দুশ্চিন্তায় থাকেন, কিন্তু সমস্যার মূল প্রোডাকশন ফ্লোরে নয়—থাকে প্রাক-পরিকল্পনা ও ব্যালেন্সিং ড্রাফটে।\n\n"
            "২৩+ বছরের ইন্ডাস্ট্রিয়াল অভিজ্ঞতা থেকে ৩টি ডেটা-ড্রিভেন টেকনিক্যাল পর্যবেক্ষণ:\n\n"
            "🔹 ১. সাইকেল টাইম বনাম পিচ টাইম (Pitch Time vs Cycle Time):\n"
            "লাইনের মোট SAM-কে ম্যানপাওয়ার দিয়ে ভাগ করে পিচ টাইম বের করুন। যেসব অপারেশনের সাইকেল টাইম পিচ টাইমের বেশি, সেখানেই বটলনেক তৈরি হয়।\n\n"
            "🔹 ২. ওয়ার্ক-ইন-প্রগ্রেস (WIP) ব্যালেন্সিং:\n"
            "অতিরিক্ত WIP এফিসিয়েন্সি বাড়ায় না, বরং বটলনেক লুকিয়ে রাখে। ৩-৪ পিসের বাফার রেখে সিঙ্গেল পিস ফ্লো কালচার তৈরি করুন।\n\n"
            "🔹 ৩. মেথড স্টাডি ও মোশন ইকোনমি:\n"
            "অপারেটরের অপ্রয়োজনীয় হাত ও চোখের মুভমেন্ট (NVA) দূর করলে প্রতিটি অপারেশনে ১০-১৫% সময় সাশ্রয় হয়।"
        )
        voiceover = (
            f"{topic_title} নিয়ে আজকের টেকনিক্যাল আলোচনা। ইন্ডাস্ট্রিতে ২৩ বছরের বাস্তব অভিজ্ঞতা থেকে দেখেছি, "
            "লাইনে ৫০ শতাংশের বেশি এফিসিয়েন্সি লস হয় ভুল ব্যালেন্সিং এবং নন-ভ্যালু অ্যাডেড কাজের কারণে। "
            "আগে পিচ টাইম ক্যালকুলেট করুন, তারপর স্কিল অনুযায়ী ক্যাপাসিটি ম্যাচ করুন।"
        )
        slides = ["১. SAM ও পিচ টাইম বিশ্লেষণ", "২. বটলনেক ও ক্যাপাসিটি ম্যাচিং", "৩. স্কিল ম্যাট্রিক্স ও লাইন এফিসিয়েন্সি"]
        bullets = ["পিচ টাইম ব্যালেন্স চার্ট", "অপ্রয়োজনীয় মোশন ও NVA রোধ", "আওয়ারলি মনিটরিং ও ব্যালেন্সিং"]

    platform_captions = build_platform_captions(master_caption, topic_title, keywords or default_tags, persona)

    return {
        "caption": platform_captions.get("linkedin_personal" if persona == "personal" else "linkedin_company"),
        "platform_captions": platform_captions,
        "voiceover": voiceover,
        "slides": slides,
        "badge": badge,
        "bullets": bullets
    }


def generate_content(topic_title: str, keywords: str, content_type: str) -> dict:
    """
    Generates high-retention, technical Bengali content using Gemini Flash (gemini-3.6-flash)
    with temperature=0.3, top_p=0.85, and environment-based persona architecture.
    Produces multi-platform tailored captions respecting each platform's character limit.
    """
    persona = settings.PROFILE_TYPE
    system_instruction = get_system_instruction(persona)
    logger.info(f"কনটেন্ট জেনারেশন পার্সোনা: [{persona.upper()}] (Model: {settings.GEMINI_MODEL}, Temp: {settings.GEMINI_TEMPERATURE})")

    if not client or not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY অনুপস্থিত। ডাইনামিক পার্সোনা অনুযায়ী ফলব্যাক ডেটা তৈরি হচ্ছে।")
        return get_fallback_content(topic_title, keywords, content_type, persona)

    prompt = f"""
    বিষয় (Topic): {topic_title}
    কีย์ওয়ার্ড / হ্যাশট্যাগ: {keywords}
    কনটেন্ট ফরম্যাট (Content Type): {content_type} (allowed: video, image, text_only)
    টার্গেট পার্সোনা: {persona}

    পোস্টের অপরিহার্য গঠন (Mandatory Structure):
    1. একটি জোরালো হুক লাইন (Strong Hook Line) যা পাঠকের দৃষ্টি আকর্ষণ করবে।
    2. মূল টেকনিক্যাল বা প্রসেস বিশ্লেষণ (Actionable Body) - ডেটা, মেথডলজি, সমীকরণ ও ব্যবহারিক ফ্লোর গাইড।
    3. বাস্তবসম্মত টেকঅ্যাওয়ে (Key Takeaways) - সংক্ষেপে ৩টি পয়েন্ট।
    4. ৩ থেকে ৫টি অত্যন্ত প্রাসঙ্গিক প্রফেশনাল হ্যাশট্যাগ।

    আউটপুটটি অবশ্যই সম্পূর্ণ বৈধ JSON অবজেক্ট হিসেবে প্রদান করো (কোনো ব্যাকটিক বা অতিরিক্ত টেক্সট ছাড়া):
    {{
      "caption": "সম্পূর্ণ পোস্টের মূল আকর্ষণীয় বাংলা ক্যাপশন (হুক + টেকনিক্যাল বিশ্লেষণ + টেকঅ্যাওয়ে + হ্যাশট্যাগ)",
      "voiceover": "ভিডিও ফরম্যাটের জন্য ৩০–৫০ সেকেন্ডের জোরালো ও প্রাঞ্জল টেকনিক্যাল ভয়েসওভার স্ক্রিপ্ট",
      "slides": ["স্লাইড ১ এর সারসংক্ষেপ", "স্লাইড ২ এর সারসংক্ষেপ", "স্লাইড ৩ এর সারসংক্ষেপ"],
      "badge": "টপিকের জন্য উপযুক্ত ক্যাটাগরি ব্যাজ (২-৩ শব্দ)",
      "bullets": ["মূল টেকঅ্যাওয়ে ১", "মূল টেকঅ্যাওয়ে ২", "মূল টেকঅ্যাওয়ে ৩"]
    }}
    """

    gen_config = types.GenerateContentConfig(
        temperature=settings.GEMINI_TEMPERATURE,
        top_p=settings.GEMINI_TOP_P,
        system_instruction=system_instruction
    )

    models_to_try = [
        settings.GEMINI_MODEL,
        "gemini-3.6-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.1-pro-preview",
        "gemini-pro-latest",
        "gemini-1.5-pro"
    ]

    seen = set()
    unique_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

    for model_name in unique_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=gen_config
            )

            cleaned_json = _clean_json_string(response.text)
            data = json.loads(cleaned_json)

            master_caption = data.get("caption", f"{topic_title}\n\n{keywords}")
            data.setdefault("voiceover", f"{topic_title} নিয়ে আজকের টেকনিক্যাল আলোচনা।")
            data.setdefault("slides", ["ভূমিকা ও প্রেক্ষাপট", "মূল আলোচনা", "ফলাফল"])
            data.setdefault("badge", "টেকনিক্যাল গাইড")
            data.setdefault("bullets", ["দক্ষতা বৃদ্ধি", "অপচয় হ্রাস", "সঠিক পর্যবেক্ষণ"])

            # Build platform-specific tailored captions respecting character limits
            platform_captions = build_platform_captions(master_caption, topic_title, keywords, persona)
            data["platform_captions"] = platform_captions

            logger.info(f"✅ Gemini API ({model_name}) থেকে সফলভাবে মাল্টি-প্ল্যাটফর্ম কনটেন্ট জেনারেট হয়েছে।")
            return data

        except Exception as e:
            logger.warning(f"মডেল {model_name} দিয়ে জেনারেশন ব্যর্থ ({e})। পরবর্তী মডেল বা ফলব্যাকে চেষ্টা করা হচ্ছে...")

    logger.warning("সকল মডেল কল ব্যর্থ বা কোটা সীমাবদ্ধতা। ডাইনামিক পার্সোনা ফলব্যাক ব্যবহার করা হচ্ছে।")
    return get_fallback_content(topic_title, keywords, content_type, persona)
