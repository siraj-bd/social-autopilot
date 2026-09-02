import json
import re
from datetime import datetime
from google import genai
from google.genai import types
from config import settings, logger

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


def get_fallback_content(topic_title: str, keywords: str, content_type: str, persona: str) -> dict:
    """Provides high-depth, persona-specific Bengali fallback content matching structured guidelines."""
    if persona == "company":
        default_tags = "#ApparelSewingProcess #GarmentTechnology #SewingMethods #QualityControl #RMGIndustry"
        badge = "সেলাই ও কোয়ালিটি গাইড"
        
        if content_type == "video":
            return {
                "caption": (
                    f"🧵 [Apparel Sewing Process] {topic_title}\n\n"
                    "পোশাক তৈরিতে সঠিক সেলাই পদ্ধতি ও মেশিনের সুনির্দিষ্ট সেটিং নিশ্চিত না করলে কোয়ালিটি ফল্ট এড়ানো অসম্ভব।\n\n"
                    "⚙️ প্রসেস গাইডলাইন:\n"
                    "• সঠিক সুই (Needle size) ও থ্রেড টেনশন নির্বাচন।\n"
                    "• মেটেরিয়াল ফিডিং এবং প্রেসার ফুট প্রেসার অ্যাডজাস্টমেন্ট।\n"
                    "• স্ট্যান্ডার্ড সিম এলাউন্স এবং সিম স্ট্রেন্থ মনিটরিং।\n\n"
                    "💡 মূল টেকঅ্যাওয়ে:\n"
                    "সঠিক প্রসেস ফলো করলে সিম পাকার বা স্কিপ স্টিচ ৯০% পর্যন্ত কমানো সম্ভব।\n\n"
                    f"{keywords or default_tags}"
                ),
                "voiceover": (
                    f"স্বাগতম অ্যাপারেল সুইং প্রসেস টেকনিক্যাল গাইডে। আজকের আলোচনার বিষয় {topic_title}। "
                    "পোশাক শিল্পে সেলাইয়ের নিখুঁত মান বজায় রাখতে হলে মেশিন মেকানিজম ও ফ্যাব্রিক ক্যারেক্টার বোঝা অত্যন্ত জরুরি। "
                    "সঠিক সুঁই, সুতার টেনশন এবং ফিড মেকানিজমের সমন্বয় রক্ষা করুন। বিস্তারিত জানতে আমাদের সাথেই থাকুন।"
                ),
                "slides": [
                    "১. সুই ও থ্রেড টেনশন অ্যাডজাস্টমেন্ট",
                    "২. সিম কোয়ালিটি ও ফল্ট প্রিভেনশন",
                    "৩. স্ট্যান্ডার্ড অপারেটিং প্রসিডিউর (SOP)"
                ],
                "badge": badge,
                "bullets": [
                    "সঠিক নিডল ও টেনশন সেটিং",
                    "স্কিপ স্টিচ ও পাকার প্রতিরোধ",
                    "স্ট্যান্ডার্ড সিম কোয়ালিটি"
                ]
            }
        elif content_type == "image":
            return {
                "caption": (
                    f"📐 [Apparel Sewing Process] {topic_title}\n\n"
                    "গার্মেন্টস সুইং ফ্লোরে নিখুঁত কোয়ালিটি এবং স্ট্যান্ডার্ড মেথড বজায় রাখার জন্য নিচে ৩টি আবশ্যকীয় নিয়ম তুলে ধরা হলো:\n\n"
                    "১. নিডল-থ্রেড কম্প্যাটিবিলিটি যাচাই।\n"
                    "২. সঠিক অ্যাটাচমেন্ট এবং ফোল্ডারের ব্যবহার।\n"
                    "৩. ইন-লাইন চেকপয়েন্টে ফার্স্ট-টাইম-রাইট কোয়ালিটি নিশ্চিতকরণ।\n\n"
                    f"{keywords or default_tags}"
                ),
                "voiceover": f"অ্যাপারেল সুইং প্রসেস: {topic_title} সম্পর্কিত গুরুত্বপূর্ণ টেকনিক্যাল তথ্য।",
                "slides": ["প্রসেস ওভারভিউ", "মেশিন সেটিং", "কোয়ালিটি চেক"],
                "badge": badge,
                "bullets": [
                    "নিডল-থ্রেড ম্যাচিং নিশ্চিতকরণ",
                    "অ্যাটাচমেন্ট ও ফোল্ডার ব্যবহার",
                    "ইন-লাইন ফার্স্ট-টাইম-রাইট"
                ]
            }
        else:  # text_only
            time_tag = datetime.now().strftime("%d %b %Y, %I:%M %p")
            return {
                "caption": (
                    f"🔍 [Apparel Sewing Process Technical Breakdown]\n\n"
                    f"📌 বিষয়: {topic_title}\n\n"
                    "পোশাক শিল্পে উৎপাদনের ধারাবাহিকতা এবং বায়ার রিকোয়ারমেন্ট অনুযায়ী গুণগত মান অর্জনে সুইং মেথডলজি সবচেয়ে সংবেদনশীল ভূমিকা রাখে।\n\n"
                    "🔹 ১. মেশিন স্পেসিফিকেশন ও গেজ সেটআপ:\n"
                    "ফ্যাব্রিকের জিএসএম ও কনস্ট্রাকশন অনুযায়ী নিডল পয়েন্ট (SPI, Ball point / SES) নির্বাচন করুন।\n\n"
                    "🔹 ২. সিম ফল্ট প্রিভেনশন:\n"
                    "সিম পাকার, ওপেন সিম ও থ্রেড ব্রেকিং প্রতিরোধে ফিড ডগ হাইট এবং থ্রেড রুট সঠিক রাখুন।\n\n"
                    "🔹 ৩. স্ট্যান্ডার্ড মেথড ও অপারেটর গাইডেন্স:\n"
                    "ক্রিটিক্যাল অপারেশনে ফোল্ডার বা জিগ ব্যবহার করে হ্যান্ডেলিং টাইম কমান এবং সেলাই নিখুঁত করুন।\n\n"
                    "🎯 টেকঅ্যাওয়ে:\n"
                    "প্রতিটি সুইং লাইনে মেথড ড্রাইভেন কালচার নিশ্চিত করলেই রি-ওয়ার্ক ও ডিএইচইউ শূন্যের কোঠায় নামিয়ে আনা সম্ভব।\n\n"
                    f"🗓️ {time_tag}\n"
                    f"{keywords or default_tags}"
                ),
                "voiceover": "",
                "slides": [],
                "badge": badge,
                "bullets": []
            }

    else:  # personal persona: 23+ years IE & Manufacturing Leader
        default_tags = "#ApparelManufacturing #IndustrialEngineering #LineBalancing #SAM #LeanManufacturing"
        badge = "আইই ও ব্যালেন্সিং"

        if content_type == "video":
            return {
                "caption": (
                    f"🔥 {topic_title}\n\n"
                    "গার্মেন্টস লাইনে অপচয় এবং বটলনেক দূর করার মূল চাবিকাঠি হলো ম্যাথমেটিক্যাল ব্যালেন্সিং। ২৩ বছরের বাস্তব অভিজ্ঞতা থেকে বলছি—"
                    "শুধু টার্গেট দিলে লাইন চলে না, ট্যাক্ট টাইম ও পিচ টাইমের সঠিক সমন্বয় প্রয়োজন।\n\n"
                    "📊 মূল ফোকাস:\n"
                    "• বটলনেক অপারেশন শনাক্তকরণ ও ক্যাপাসিটি ব্যালেন্সিং।\n"
                    "• অপারেটর স্কিল ম্যাট্রিক্স অনুযায়ী ওয়ার্ক স্টেশন রি-ডিস্ট্রিবিউশন।\n"
                    "• পিচ টাইম ও সাইকেল টাইমের পার্থক্য ন্যূনতম পর্যায়ে নামিয়ে আনা।\n\n"
                    f"{keywords or default_tags}"
                ),
                "voiceover": (
                    f"{topic_title} নিয়ে আজকের টেকনিক্যাল আলোচনা। ইন্ডাস্ট্রিতে ২৩ বছরের বাস্তব অভিজ্ঞতা থেকে দেখেছি, "
                    "লাইনে ৫০ শতাংশের বেশি এফিসিয়েন্সি লস হয় ভুল ব্যালেন্সিং এবং নন-ভ্যালু অ্যাডেড কাজের কারণে। "
                    "আগে পিচ টাইম ক্যালকুলেট করুন, তারপর স্কিল অনুযায়ী ক্যাপাসিটি ম্যাচ করুন। বিস্তারিত দেখুন ভিডিওতে।"
                ),
                "slides": [
                    "১. SAM ও পিচ টাইম বিশ্লেষণ",
                    "২. বটলনেক ও ক্যাপাসিটি ম্যাচিং",
                    "৩. স্কিল ম্যাট্রিক্স ও লাইন এফিসিয়েন্সি"
                ],
                "badge": badge,
                "bullets": [
                    "SAM ও পিচ টাইম নির্ধারণ",
                    "বটলনেক অপচয় দূরীকরণ",
                    "স্কিল ভিত্তিক ওয়ার্ক ডিস্ট্রিবিউশন"
                ]
            }
        elif content_type == "image":
            return {
                "caption": (
                    f"📈 {topic_title}\n\n"
                    "২৩ বছরের ফ্যাক্টরি ম্যানেজমেন্ট অভিজ্ঞতায় একটি সত্য স্পষ্ট: লাইন ব্যালেন্সিং সঠিক হলে লাইনের এফিসিয়েন্সি ২০% পর্যন্ত রাতারাতি বাড়ানো সম্ভব।\n\n"
                    "নিচের ৩টি প্রধান মেথডলজিকাল পয়েন্ট লাইনে বাস্তবায়ন করুন:\n\n"
                    "১. সাইকেল টাইম ও পিচ টাইমের ব্যালেন্স চার্ট তৈরি।\n"
                    "২. ওয়ার্ক স্টেশনে মেথড ইমপ্রুভমেন্ট (NVA এলিমিনেশন)।\n"
                    "৩. রিয়েল-টাইম আওয়ারলি ট্র্যাকিং ও তাৎক্ষণিক অ্যাকশন।\n\n"
                    f"{keywords or default_tags}"
                ),
                "voiceover": f"ইন্ডাস্ট্রিয়াল ইঞ্জিনিয়ারিং এক্সপার্ট গাইড: {topic_title}।",
                "slides": ["SAM বিশ্লেষণ", "ক্যাপাসিটি ব্যালেন্স", "এফিসিয়েন্সি বৃদ্ধি"],
                "badge": badge,
                "bullets": [
                    "পিচ টাইম ব্যালেন্স চার্ট",
                    "অপ্রয়োজনীয় মোশন ও NVA রোধ",
                    "আওয়ারলি মনিটরিং ও ব্যালেন্সিং"
                ]
            }
        else:  # text_only
            time_tag = datetime.now().strftime("%d %b %Y, %I:%M %p")
            return {
                "caption": (
                    f"💼 [Manufacturing Leader Insights] {topic_title}\n\n"
                    "গার্মেন্টস ফ্লোরে অনেকেই লাইন এফিসিয়েন্সি নিয়ে দুশ্চিন্তায় থাকেন, কিন্তু সমস্যার মূল প্রোডাকশন ফ্লোরে নয়—থাকে প্রাক-পরিকল্পনা ও ব্যালেন্সিং ড্রাফটে।\n\n"
                    "২৩+ বছরের ইন্ডাস্ট্রিয়াল অভিজ্ঞতা থেকে ৩টি ডেটা-ড্রিভেন টেকনিক্যাল পর্যবেক্ষণ:\n\n"
                    "🔹 ১. সাইকেল টাইম বনাম পিচ টাইম (Pitch Time vs Cycle Time):\n"
                    "লাইনের মোট SAM-কে ম্যানপাওয়ার দিয়ে ভাগ করে পিচ টাইম বের করুন। যেসব অপারেশনের সাইকেল টাইম পিচ টাইমের বেশি, সেখানেই বটলনেক তৈরি হয়।\n\n"
                    "🔹 ২. ওয়ার্ক-ইন-প্রগ্রেস (WIP) ব্যালেন্সিং:\n"
                    "অতিরিক্ত WIP এফিসিয়েন্সি বাড়ায় না, বরং বটলনেক লুকিয়ে রাখে। ৩-৪ পিসের বাফার রেখে সিঙ্গেল পিস ফ্লো কালচার তৈরি করুন।\n\n"
                    "🔹 ৩. মেথড স্টাডি ও মোশন ইকোনমি:\n"
                    "অপারেটরের অপ্রয়োজনীয় হাত ও চোখের মুভমেন্ট (NVA) দূর করলে প্রতিটি অপারেশনে ১০-১৫% সময় সাশ্রয় হয়।\n\n"
                    "🎯 বাস্তবসম্মত টেকঅ্যাওয়ে:\n"
                    "ম্যানেজমেন্টের দায়িত্ব শুধু টার্গেট চাপিয়ে দেওয়া নয়, বরং সঠিক আইই টুলস দিয়ে কর্মীদের কাজ সহজ করা।\n\n"
                    f"🗓️ {time_tag}\n"
                    f"{keywords or default_tags}"
                ),
                "voiceover": "",
                "slides": [],
                "badge": badge,
                "bullets": []
            }


def generate_content(topic_title: str, keywords: str, content_type: str) -> dict:
    """
    Generates high-retention, technical Bengali content using Gemini Pro (gemini-1.5-pro)
    with temperature=0.3, top_p=0.85, and environment-based persona architecture.
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
      "caption": "সম্পূর্ণ পোস্টের বিস্তারিত আকর্ষণীয় বাংলা ক্যাপশন (হুক + টেকনিক্যাল বিশ্লেষণ + টেকঅ্যাওয়ে + হ্যাশট্যাগ)",
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

    # Remove duplicates while preserving order
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

            data.setdefault("caption", f"{topic_title}\n\n{keywords}")
            data.setdefault("voiceover", f"{topic_title} নিয়ে আজকের টেকনিক্যাল আলোচনা।")
            data.setdefault("slides", ["ভূমিকা ও প্রেক্ষাপট", "মূল আলোচনা", "ফলাফল"])
            data.setdefault("badge", "টেকনিক্যাল গাইড")
            data.setdefault("bullets", ["দক্ষতা বৃদ্ধি", "অপচয় হ্রাস", "সঠিক পর্যবেক্ষণ"])

            logger.info(f"✅ Gemini API ({model_name}) থেকে সফলভাবে কনটেন্ট জেনারেট হয়েছে।")
            return data

        except Exception as e:
            logger.warning(f"মডেল {model_name} দিয়ে জেনারেশন ব্যর্থ ({e})। পরবর্তী মডেল বা ফলব্যাকে চেষ্টা করা হচ্ছে...")

    logger.warning("সকল মডেল কল ব্যর্থ বা কোটা সীমাবদ্ধতা। ডাইনামিক পার্সোনা ফলব্যাক ব্যবহার করা হচ্ছে।")
    return get_fallback_content(topic_title, keywords, content_type, persona)
