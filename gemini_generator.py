import json
import re
from datetime import datetime
from typing import Dict, Optional
from google import genai
from google.genai import types
from config import settings, logger, get_platform_registry

# Initialize client only if GEMINI_API_KEY is available
client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None


def get_system_instruction(persona: str, lang: str = "en") -> str:
    """Returns the dedicated system instruction based on active profile persona and language."""
    is_bengali = lang.lower() in ["bn", "bangla", "bengali"]

    if not is_bengali:
        # Default English System Instructions
        if persona == "company":
            return """
You are the official technical and engineering editorial voice of "Apparel Sewing Process".
Your core focus:
1. Modern sewing technology, automation, and machine attachments in apparel manufacturing.
2. Sewing process flow optimization and Standard Operating Procedures (SOP).
3. Quality control standards (AQL, defect reduction, seam puckering, skip stitch prevention).
4. Industrial machine guides (SNLS, Overlock, Flatlock, Feed-off-the-arm, Auto-Jigs) and technical settings.
5. Standard manufacturing methods and floor best practices.

Tone & Style: Authoritative, institutional, educational, precise, and process-driven English.
Language: Professional, high-standard English.
"""
        else:  # personal persona
            return """
You are a renowned Apparel Manufacturing Leader and Industrial Engineering (IE) Expert with 23+ years of hands-on factory floor experience.
Your core focus:
1. Deep technical analysis and data-driven decision making in garment manufacturing.
2. SAM / SMV calculations, method study, time study, and work measurement.
3. Line balancing, pitch time, takt time, and cycle time optimization.
4. Line efficiency loss reduction, bottleneck identification, and practical problem solving.
5. Lean manufacturing, 5S, WIP control, and real-time production tracking.

Tone & Style: Senior executive leadership, practical, highly analytical, data-grounded, and reflective of 23+ years on factory floors.
Language: Professional, executive English.
"""

    else:
        # Optional Bengali Mode (Preserving all technical terms in English)
        if persona == "company":
            return """
তুমি হলে "Apparel Sewing Process" এর অফিসিয়াল প্রাতিষ্ঠানিক টেকনিক্যাল অ্যান্ড ইঞ্জিনিয়ারিং পাবলিকেশন পেজ।
তোমার মূল ফোকাস:
1. পোশাক শিল্পের আধুনিক সেলাই টেকনোলজি (Modern Sewing Technology & Automations)।
2. সুইং প্রসেস ফ্লো (Process Flow) ও স্ট্যান্ডার্ড অপারেটিং প্রসিডিউর (SOP)।
3. কোয়ালিটি কন্ট্রোল স্ট্যান্ডার্ড (AQL, Defect Reduction, Seam Puckering / Skip Stitch Prevention)।
4. বিভিন্ন সুইং মেশিন গাইড (Single Needle, Overlock, Flatlock, Feed-off-the-arm, Auto-Jigs) এবং অ্যাটাচমেন্ট ব্যবহার।
5. ইন্ডাস্ট্রিয়াল বেস্ট প্র্যাকটিস ও স্ট্যান্ডার্ড মেথড।

টোন ও স্টাইল: প্রাতিষ্ঠানিক, শিক্ষণীয়, স্পষ্ট, প্রসেস-ভিত্তিক এবং নির্ভরযোগ্য।
ভাষা নির্দেশিকা: মূল বাক্য প্রমিত বাংলায় হবে, কিন্তু সমস্ত প্রয়োজনীয় টেকনিক্যাল টার্ম (যেমন: RMG, SOP, AQL, Seam Puckering, Skip Stitch, SPI, Needle, Gauge, Feed Dog) কোনো অপ্রয়োজনীয় অনুবাদ ছাড়াই ইংরেজিতে অক্ষুণ্ণ রাখতে হবে।
"""
        else:  # personal persona
            return """
তুমি হলে একজন খ্যাতনামা Apparel Manufacturing Leader এবং Industrial Engineering (IE) Expert যার গার্মেন্টস ইন্ডাস্ট্রিতে ২৩+ বছরের বাস্তব অভিজ্ঞতা রয়েছে।
তোমার মূল ফোকাস:
1. গভীর টেকনিক্যাল বিশ্লেষণ ও ডেটা-ড্রিভেন সিদ্ধান্ত (Data-Driven Decision Making)।
2. SAM / SMV ক্যালকুলেশন, মেথড স্টাডি এবং টাইম স্টাডি।
3. লাইন ব্যালেন্সিং (Line Balancing), পিচ টাইম (Pitch Time), এবং ট্যাক্ট টাইম (Takt Time) অপটিমাইজেশন।
4. লাইন এফিসিয়েন্সি লস (Efficiency Loss) ও বটলনেক (Bottleneck) চিহ্নিতকরণ ও সমাধান।
5. লীন ম্যানুফ্যাকচারিং (Lean Manufacturing), 5S, WIP ব্যালেন্সিং এবং রিয়েল-টাইম প্রোডাকশন ট্র্যাকিং।

টোন ও স্টাইল: অভিজ্ঞ লিডারশিপ টোন, প্র্যাকটিক্যাল, গাণিতিক/ডেটা সমৃদ্ধ এবং ফ্যাক্টরি ফ্লোরের বাস্তব অভিজ্ঞতাসম্পন্ন।
ভাষা নির্দেশিকা: মূল বাক্য প্রমিত বাংলায় হবে, কিন্তু সমস্ত টেকনিক্যাল টার্ম (যেমন: SAM, SMV, Line Balancing, Pitch Time, Takt Time, Cycle Time, Bottleneck, WIP, NVA, 5S, Lean) কোনো বিকৃতি বা অপ্রয়োজনীয় অনুবাদ ছাড়াই ইংরেজিতে অক্ষুণ্ণ রাখতে হবে।
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


def build_platform_captions(master_caption: str, topic: str, keywords: str, persona: str, lang: str = "en") -> Dict[str, str]:
    """
    Constructs platform-optimized captions respecting each platform's character limit, audience tone, and selected language.
    """
    time_tag = datetime.now().strftime("%d %b %Y, %I:%M %p")
    registry = get_platform_registry()
    is_bengali = lang.lower() in ["bn", "bangla", "bengali"]

    clean_topic = topic.strip()
    clean_kw = keywords.strip() if keywords else ("#ApparelManufacturing #IndustrialEngineering" if not is_bengali else "#RMG #IndustrialEngineering")

    if not is_bengali:
        # English Platform Adaptations (Default)
        li_personal = (
            f"💼 [Manufacturing Leader Insights] {clean_topic}\n\n"
            f"{master_caption}\n\n"
            f"🎯 Key Takeaway:\n"
            f"Applying rigorous method study and mathematical line balancing is the only sustainable way to eliminate floor bottlenecks and protect line efficiency.\n\n"
            f"🗓️ {time_tag}\n"
            f"{clean_kw}"
        )
        if len(li_personal) > registry["linkedin_personal"].max_characters:
            li_personal = li_personal[:registry["linkedin_personal"].max_characters - 10] + "..."

        li_company = (
            f"🔍 [Apparel Sewing Process Technical Hub] {clean_topic}\n\n"
            f"{master_caption}\n\n"
            f"⚙️ Ensure adherence to Standard Operating Procedures (SOP) to achieve first-time-right quality on the sewing floor.\n\n"
            f"🗓️ {time_tag}\n"
            f"{clean_kw}"
        )
        if len(li_company) > registry["linkedin_company"].max_characters:
            li_company = li_company[:registry["linkedin_company"].max_characters - 10] + "..."

        fb_caption = (
            f"📢 {clean_topic}\n\n"
            f"{master_caption}\n\n"
            f"💬 How are you implementing these techniques on your production floor? Share your thoughts and experience below!\n\n"
            f"👉 Follow our page for daily industrial engineering & manufacturing insights.\n\n"
            f"{clean_kw}"
        )
        if len(fb_caption) > registry["facebook_page"].max_characters:
            fb_caption = fb_caption[:registry["facebook_page"].max_characters - 10] + "..."

        body_short = master_caption[:600] if len(master_caption) > 600 else master_caption
        ig_caption = (
            f"✨ {clean_topic}\n\n"
            f"{body_short}\n\n"
            f"📌 Save this post for your factory floor reference and share with your production team.\n\n"
            f"{clean_kw}"
        )
        if len(ig_caption) > registry["instagram"].max_characters:
            ig_caption = ig_caption[:registry["instagram"].max_characters - 10] + "..."

    else:
        # Bengali Platform Adaptations (Optional Mode)
        li_personal = (
            f"💼 [Manufacturing Leader Insights] {clean_topic}\n\n"
            f"{master_caption}\n\n"
            f"🎯 বাস্তবসম্মত টেকঅ্যাওয়ে:\n"
            f"সঠিক Method Study ও ডেটা-ড্রিভেন Line Balancing নিশ্চিত করলেই ফ্লোরে অপচয় ও Bottleneck দূর করা সম্ভব।\n\n"
            f"🗓️ {time_tag}\n"
            f"{clean_kw}"
        )
        if len(li_personal) > registry["linkedin_personal"].max_characters:
            li_personal = li_personal[:registry["linkedin_personal"].max_characters - 10] + "..."

        li_company = (
            f"🔍 [Apparel Sewing Process Technical Hub] {clean_topic}\n\n"
            f"{master_caption}\n\n"
            f"⚙️ স্ট্যান্ডার্ড অপারেটিং প্রসিডিউর (SOP) মেনে সুইং ফ্লোরে First-Time-Right কোয়ালিটি ও উৎপাদনশীলতা নিশ্চিত করুন।\n\n"
            f"🗓️ {time_tag}\n"
            f"{clean_kw}"
        )
        if len(li_company) > registry["linkedin_company"].max_characters:
            li_company = li_company[:registry["linkedin_company"].max_characters - 10] + "..."

        fb_caption = (
            f"📢 {clean_topic}\n\n"
            f"{master_caption}\n\n"
            f"💬 আপনার ফ্যাক্টরি ফ্লোরে এই পদ্ধতি কীভাবে প্রয়োগ করছেন? আপনার মূল্যবান অভিজ্ঞতা কমেন্টে শেয়ার করুন।\n\n"
            f"👉 নিয়মিত টেকনিক্যাল আপডেটের জন্য আমাদের পেজে লাইক ও ফলো দিয়ে সাথে থাকুন।\n\n"
            f"{clean_kw}"
        )
        if len(fb_caption) > registry["facebook_page"].max_characters:
            fb_caption = fb_caption[:registry["facebook_page"].max_characters - 10] + "..."

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


def get_fallback_content(topic_title: str, keywords: str, content_type: str, persona: str, lang: str = "en") -> dict:
    """Provides high-depth, language-aware persona fallback content."""
    is_bengali = lang.lower() in ["bn", "bangla", "bengali"]

    if not is_bengali:
        # Default English Fallbacks
        if persona == "company":
            default_tags = "#ApparelSewingProcess #GarmentTechnology #QualityControl #SewingMethods #RMGIndustry"
            badge = "Technical Guide"
            master_caption = (
                "Achieving consistent product quality and meeting international buyer specifications requires rigorous adherence to standardized sewing methodologies.\n\n"
                "🔹 1. Machine Specification & Needle Setup:\n"
                "Match needle size and point geometry (Ball point, SES, SPI) precisely with fabric GSM and weave structure.\n\n"
                "🔹 2. Seam Defect Prevention:\n"
                "Prevent seam puckering, open seams, and thread breakage by calibrating feed dog height and thread tension paths.\n\n"
                "🔹 3. Standard Operating Procedures (SOP):\n"
                "Deploy engineered work aids, folders, and jigs on critical operations to reduce handling time and secure first-time-right quality."
            )
            voiceover = (
                f"Welcome to the Apparel Sewing Process technical guide. Today's focus is {topic_title}. "
                "Maintaining flawless sewing quality requires a thorough understanding of machine mechanics and fabric characteristics. "
                "Ensure proper alignment between needle size, thread tension, and material feeding mechanisms."
            )
            slides = ["1. Needle & Thread Calibration", "2. Seam Quality & Defect Prevention", "3. Standard Operating Procedure (SOP)"]
            bullets = ["Needle-Thread Matching", "Work Aids & Folders", "First-Time-Right Quality"]

        else:  # personal persona
            default_tags = "#ApparelManufacturing #IndustrialEngineering #LineBalancing #SAM #LeanManufacturing"
            badge = "IE & Operations"
            master_caption = (
                "Floor managers often struggle with line efficiency losses, but the root cause rarely lies on the sewing line itself—it stems from pre-production balancing drafts.\n\n"
                "Drawing from 23+ years of industrial engineering leadership on factory floors, here are 3 data-driven observations:\n\n"
                "🔹 1. Pitch Time vs. Cycle Time Analysis:\n"
                "Calculate pitch time by dividing total garment SAM by allocated manpower. Any workstation where cycle time exceeds pitch time creates an automatic bottleneck.\n\n"
                "🔹 2. Work-In-Progress (WIP) Balancing:\n"
                "Excessive WIP does not boost output—it hides defects and starves downstream operators. Maintain a lean buffer of 3-4 pieces per workstation.\n\n"
                "🔹 3. Method Study & Motion Economy:\n"
                "Eliminate non-value-added (NVA) hand movements. A 2-second reduction per cycle yields substantial capacity gains across an entire shift."
            )
            voiceover = (
                f"Today we analyze {topic_title}. In 23 years on factory floors, I have seen over 50% of efficiency losses caused by poor line balancing and unnecessary operator motion. "
                "Calculate your pitch time first, eliminate non-value-added movements, and align operator skill matrices for maximum throughput."
            )
            slides = ["1. SAM & Pitch Time Analysis", "2. Bottleneck & Capacity Matching", "3. Skill Matrix & Line Efficiency"]
            bullets = ["Pitch Time Balance Chart", "NVA Motion Elimination", "Hourly Tracking & Balance"]

    else:
        # Optional Bengali Mode (with English Technical Terms)
        if persona == "company":
            default_tags = "#ApparelSewingProcess #GarmentTechnology #SewingMethods #QualityControl #RMGIndustry"
            badge = "সেলাই ও কোয়ালিটি গাইড"
            master_caption = (
                "পোশাক শিল্পে উৎপাদনের ধারাবাহিকতা এবং বায়ার রিকোয়ারমেন্ট অনুযায়ী গুণগত মান অর্জনে সুইং মেথডলজি সবচেয়ে সংবেদনশীল ভূমিকা রাখে।\n\n"
                "🔹 ১. মেশিন স্পেসিফিকেশন ও গেজ সেটআপ:\n"
                "ফ্যাব্রিকের GSM ও কনস্ট্রাকশন অনুযায়ী নিডল পয়েন্ট (SPI, Ball point / SES) নির্বাচন করুন।\n\n"
                "🔹 ২. Seam Defect Prevention:\n"
                "Seam Puckering, Open Seam ও Thread Breaking প্রতিরোধে Feed Dog হাইট এবং থ্রেড রুট সঠিক রাখুন।\n\n"
                "🔹 ৩. স্ট্যান্ডার্ড মেথড ও SOP:\n"
                "ক্রিটিক্যাল অপারেশনে Folder বা Jig ব্যবহার করে Handling Time কমান এবং সেলাই First-Time-Right রাখুন।"
            )
            voiceover = (
                f"স্বাগতম অ্যাপারেল সুইং প্রসেস টেকনিক্যাল গাইডে। আজকের আলোচনার বিষয় {topic_title}। "
                "পোশাক শিল্পে সেলাইয়ের নিখুঁত মান বজায় রাখতে হলে মেশিন মেকানিজম ও ফ্যাব্রিক ক্যারেক্টার বোঝা অত্যন্ত জরুরি। "
                "সঠিক নিডল, থ্রেড টেনশন এবং ফিড মেকানিজমের সমন্বয় রক্ষা করুন।"
            )
            slides = ["১. সুই ও থ্রেড টেনশন অ্যাডজাস্টমেন্ট", "২. সিম কোয়ালিটি ও ফল্ট প্রিভেনশন", "৩. স্ট্যান্ডার্ড অপারেটিং প্রসিডিউর (SOP)"]
            bullets = ["Needle-Thread ম্যাচিং নিশ্চিতকরণ", "Work Aids ও Folder ব্যবহার", "First-Time-Right কোয়ালিটি"]

        else:  # personal persona
            default_tags = "#ApparelManufacturing #IndustrialEngineering #LineBalancing #SAM #LeanManufacturing"
            badge = "আইই ও ব্যালেন্সিং"
            master_caption = (
                "গার্মেন্টস ফ্লোরে অনেকেই লাইন এফিসিয়েন্সি নিয়ে দুশ্চিন্তায় থাকেন, কিন্তু সমস্যার মূল প্রোডাকশন ফ্লোরে নয়—থাকে প্রাক-পরিকল্পনা ও ব্যালেন্সিং ড্রাফটে।\n\n"
                "২৩+ বছরের ইন্ডাস্ট্রিয়াল অভিজ্ঞতা থেকে ৩টি ডেটা-ড্রিভেন টেকনিক্যাল পর্যবেক্ষণ:\n\n"
                "🔹 ১. Cycle Time বনাম Pitch Time:\n"
                "লাইনের মোট SAM-কে ম্যানপাওয়ার দিয়ে ভাগ করে Pitch Time বের করুন। যেসব অপারেশনের Cycle Time Pitch Time-এর বেশি, সেখানেই Bottleneck তৈরি হয়।\n\n"
                "🔹 ২. Work-In-Progress (WIP) ব্যালেন্সিং:\n"
                "অতিরিক্ত WIP এফিসিয়েন্সি বাড়ায় না, বরং Bottleneck লুকিয়ে রাখে। ৩-৪ পিসের বাফার রেখে Single Piece Flow কালচার তৈরি করুন।\n\n"
                "🔹 ৩. Method Study ও Motion Economy:\n"
                "অপারেটরের অপ্রয়োজনীয় Hand & Eye Movement (NVA) দূর করলে প্রতিটি অপারেশনে ১০-১৫% সময় সাশ্রয় হয়।"
            )
            voiceover = (
                f"{topic_title} নিয়ে আজকের টেকনিক্যাল আলোচনা। ইন্ডাস্ট্রিতে ২৩ বছরের বাস্তব অভিজ্ঞতা থেকে দেখেছি, "
                "লাইনে ৫০ শতাংশের বেশি এফিসিয়েন্সি লস হয় ভুল Line Balancing এবং Non-Value-Added কাজের কারণে। "
                "আগে Pitch Time ক্যালকুলেট করুন, তারপর Skill Matrix অনুযায়ী ক্যাপাসিটি ম্যাচ করুন।"
            )
            slides = ["১. SAM ও Pitch Time বিশ্লেষণ", "২. Bottleneck ও ক্যাপাসিটি ম্যাচিং", "৩. Skill Matrix ও লাইন এফিসিয়েন্সি"]
            bullets = ["Pitch Time ব্যালেন্স চার্ট", "NVA Motion রোধ", "আওয়ারলি মনিটরিং ও ব্যালেন্সিং"]

    platform_captions = build_platform_captions(master_caption, topic_title, keywords or default_tags, persona, lang)

    return {
        "caption": platform_captions.get("linkedin_personal" if persona == "personal" else "linkedin_company"),
        "platform_captions": platform_captions,
        "voiceover": voiceover,
        "slides": slides,
        "badge": badge,
        "bullets": bullets
    }


def generate_content(topic_title: str, keywords: str, content_type: str, lang: Optional[str] = None) -> dict:
    """
    Generates high-retention, technical content using Gemini Flash (gemini-3.6-flash)
    with temperature=0.3, top_p=0.85, and environment-based persona & language architecture.
    Defaults to English, with full Bengali support.
    """
    persona = settings.PROFILE_TYPE
    selected_lang = (lang or settings.DEFAULT_LANGUAGE).strip().lower()
    system_instruction = get_system_instruction(persona, selected_lang)
    logger.info(f"কনটেন্ট জেনারেশন: Persona=[{persona.upper()}], Lang=[{selected_lang.upper()}], Model=[{settings.GEMINI_MODEL}]")

    if not client or not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY অনুপস্থিত। ডাইনামিক পার্সোনা অনুযায়ী ফলব্যাক ডেটা তৈরি হচ্ছে।")
        return get_fallback_content(topic_title, keywords, content_type, persona, selected_lang)

    lang_prompt_guide = "Output in professional, authoritative English." if selected_lang not in ["bn", "bangla", "bengali"] else "Output in native standard Bengali script (bn-BD), strictly keeping all technical RMG/IE/Production terms in English."

    prompt = f"""
    Topic: {topic_title}
    Keywords / Hashtags: {keywords}
    Content Type: {content_type} (allowed: video, image, text_only)
    Target Persona: {persona}
    Language: {selected_lang} ({lang_prompt_guide})

    Mandatory Content Structure:
    1. Strong Hook Line capturing industry leadership attention.
    2. Actionable Technical Body: data, methodology, equations, and floor-level practical guidance.
    3. Practical Key Takeaways: 3 concise bullet points.
    4. 3 to 5 highly relevant professional hashtags.

    Return ONLY a valid JSON object (no backticks, no extra text):
    {{
      "caption": "Full high-engagement master caption (Hook + Technical Body + Takeaways + Hashtags)",
      "voiceover": "30-50 second clear and authoritative voiceover script for video",
      "slides": ["Summary of Slide 1", "Summary of Slide 2", "Summary of Slide 3"],
      "badge": "2-3 word topic category badge",
      "bullets": ["Key Takeaway 1", "Key Takeaway 2", "Key Takeaway 3"]
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
            data.setdefault("voiceover", f"{topic_title} technical analysis." if selected_lang == "en" else f"{topic_title} নিয়ে আজকের টেকনিক্যাল আলোচনা।")
            data.setdefault("slides", ["Overview", "Core Analysis", "Takeaways"] if selected_lang == "en" else ["ভূমিকা ও প্রেক্ষাপট", "মূল আলোচনা", "ফলাফল"])
            data.setdefault("badge", "Technical Guide" if selected_lang == "en" else "টেকনিক্যাল গাইড")
            data.setdefault("bullets", ["Efficiency Gain", "Waste Reduction", "Quality Control"] if selected_lang == "en" else ["দক্ষতা বৃদ্ধি", "অপচয় হ্রাস", "সঠিক পর্যবেক্ষণ"])

            # Build platform-specific tailored captions respecting character limits and language
            platform_captions = build_platform_captions(master_caption, topic_title, keywords, persona, selected_lang)
            data["platform_captions"] = platform_captions

            logger.info(f"✅ Gemini API ({model_name}) থেকে সফলভাবে [{selected_lang.upper()}] কনটেন্ট জেনারেট হয়েছে।")
            return data

        except Exception as e:
            logger.warning(f"মডেল {model_name} দিয়ে জেনারেশন ব্যর্থ ({e})। পরবর্তী মডেল বা ফলব্যাকে চেষ্টা করা হচ্ছে...")

    logger.warning(f"সকল মডেল কল ব্যর্থ বা কোটা সীমাবদ্ধতা। ডাইনামিক পার্সোনা ফলব্যাক [{selected_lang.upper()}] ব্যবহার করা হচ্ছে।")
    return get_fallback_content(topic_title, keywords, content_type, persona, selected_lang)
