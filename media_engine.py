import asyncio
import textwrap
import edge_tts
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from mutagen.mp3 import MP3
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from config import settings, OUTPUT_DIR, logger


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Helper to safely load Bengali font or fallback to default."""
    try:
        return ImageFont.truetype(settings.FONT_PATH, size)
    except Exception as e:
        logger.warning(f"ফন্ট লোড করতে সমস্যা: {e}। ডিফল্ট ফন্ট ব্যবহার করা হচ্ছে।")
        return ImageFont.load_default()


def create_image_card(title: str, badge: str, bullets: list, filename: str = "card.png") -> Path:
    """Renders a modern, professional 1080x1080 Bengali social graphic card."""
    out_path = OUTPUT_DIR / filename
    width, height = 1080, 1080
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # slate-900
    draw = ImageDraw.Draw(img)

    font_title = _get_font(48)
    font_body = _get_font(34)
    font_badge = _get_font(26)
    font_footer = _get_font(24)

    # Gradient-like subtle decorative glow lines at the top
    draw.rectangle([0, 0, width, 8], fill=(59, 130, 246))

    # Badge Pill (Top-Left)
    badge_text = f"• {badge.strip()} •" if badge else "• গাইড •"
    draw.rounded_rectangle([70, 65, 360, 120], radius=12, fill=(37, 99, 235))
    draw.text((95, 78), badge_text, font=font_badge, fill=(255, 255, 255))

    # Watermark Top-Right
    draw.text((720, 80), "Social Autopilot", font=font_footer, fill=(100, 116, 139))

    # Main Title (Wrapped)
    wrapped_title = textwrap.fill(title, width=28)
    draw.text((70, 160), wrapped_title, font=font_title, fill=(248, 250, 252), spacing=14)

    # Decorative separator line
    draw.line([(70, 360), (1010, 360)], fill=(51, 65, 85), width=2)

    # 3 Takeaway Cards
    y_offset = 390
    card_height = 140
    for idx, bullet in enumerate(bullets[:3]):
        # Card container
        draw.rounded_rectangle(
            [70, y_offset, 1010, y_offset + card_height],
            radius=16,
            fill=(30, 41, 59),  # slate-800
            outline=(51, 65, 85),
            width=2
        )

        # Number circle badge
        draw.ellipse([95, y_offset + 42, 150, y_offset + 97], fill=(16, 185, 129))
        draw.text((114, y_offset + 50), str(idx + 1), font=font_badge, fill=(255, 255, 255))

        # Bullet text
        wrapped_bullet = textwrap.fill(bullet, width=38)
        draw.text((175, y_offset + 36), wrapped_bullet, font=font_body, fill=(241, 245, 249), spacing=8)

        y_offset += card_height + 25

    # Footer Branding Bar
    draw.line([(70, 970), (1010, 970)], fill=(51, 65, 85), width=1)
    draw.text((70, 995), "⚡ 100% Free & Self-Hosted Automation", font=font_footer, fill=(148, 163, 184))
    draw.text((820, 995), "Auto-Generated", font=font_footer, fill=(100, 116, 139))

    img.save(out_path, quality=95)
    logger.info(f"ইমেজ কার্ড তৈরি হয়েছে: {out_path}")
    return out_path


async def generate_voiceover_async(text: str, filename: str = "voiceover.mp3") -> Path:
    """Synthesizes high quality Bengali neural voiceover using Edge TTS."""
    out_path = OUTPUT_DIR / filename
    cleaned_text = text.replace("\n", " ").strip()
    if not cleaned_text:
        cleaned_text = "সোশ্যাল অটোপাইলট স্বয়ংক্রিয় কন্টেন্ট জেনারেশন।"

    communicate = edge_tts.Communicate(cleaned_text, settings.TTS_VOICE)
    await communicate.save(str(out_path))
    logger.info(f"ভয়েসওভার সফলভাবে তৈরি হয়েছে: {out_path}")
    return out_path


def generate_voiceover(text: str, filename: str = "voiceover.mp3") -> Path:
    """Synchronous wrapper for generate_voiceover_async."""
    return asyncio.run(generate_voiceover_async(text, filename))


def create_vertical_video(title: str, slides: list, audio_path: Path, filename: str = "short.mp4") -> Path:
    """Renders 1080x1920 portrait vertical video (9:16 Shorts/Reels) synchronized with voiceover."""
    out_video_path = OUTPUT_DIR / filename
    
    # Calculate audio duration accurately
    audio_info = MP3(str(audio_path))
    total_duration = max(float(audio_info.info.length), 3.0)
    
    slide_list = slides if slides else ["ভূমিকা ও প্রেক্ষাপট", "মূল আলোচনা", "সারসংক্ষেপ ও ফলাফল"]
    num_slides = len(slide_list)
    slide_duration = total_duration / num_slides

    font_title = _get_font(56)
    font_slide_text = _get_font(44)
    font_meta = _get_font(32)

    temp_files = []
    clips = []

    try:
        for idx, slide_text in enumerate(slide_list):
            img = Image.new("RGB", (1080, 1920), color=(15, 23, 42))  # slate-900
            draw = ImageDraw.Draw(img)

            # Top branding accent
            draw.rectangle([0, 0, 1080, 12], fill=(56, 189, 248))
            draw.text((80, 100), "🔥 SOCIAL AUTOPILOT SHORTS", font=font_meta, fill=(56, 189, 248))

            # Main Topic Header
            wrapped_title = textwrap.fill(title, width=26)
            draw.text((80, 200), wrapped_title, font=font_title, fill=(255, 255, 255), spacing=16)

            # Center Card Container
            card_top = 700
            card_bottom = 1350
            draw.rounded_rectangle(
                [70, card_top, 1010, card_bottom],
                radius=24,
                fill=(30, 41, 59),
                outline=(56, 189, 248),
                width=3
            )

            # Slide Step Indicator
            step_str = f"ধাপ {idx + 1} / {num_slides}"
            draw.rounded_rectangle([110, card_top + 40, 320, card_top + 100], radius=12, fill=(37, 99, 235))
            draw.text((140, card_top + 52), step_str, font=font_meta, fill=(255, 255, 255))

            # Slide Text Content
            wrapped_slide = textwrap.fill(slide_text, width=28)
            draw.text((110, card_top + 180), wrapped_slide, font=font_slide_text, fill=(241, 245, 249), spacing=22)

            # Bottom Progress Dots
            dot_start_x = 440
            for d in range(num_slides):
                dot_x = dot_start_x + (d * 50)
                dot_color = (56, 189, 248) if d == idx else (71, 85, 105)
                draw.ellipse([dot_x, 1720, dot_x + 20, 1740], fill=dot_color)

            draw.text((80, 1800), "🔔 সাবস্ক্রাইব ও ফলো করে সাথে থাকুন", font=font_meta, fill=(148, 163, 184))

            temp_slide_path = OUTPUT_DIR / f"_temp_slide_{idx}.png"
            img.save(temp_slide_path, quality=95)
            temp_files.append(temp_slide_path)

            clip = ImageClip(str(temp_slide_path)).with_duration(slide_duration)
            clips.append(clip)

        final_video = concatenate_videoclips(clips, method="compose")
        audio_clip = AudioFileClip(str(audio_path))
        final_video = final_video.with_audio(audio_clip).with_duration(total_duration)

        final_video.write_videofile(
            str(out_video_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None
        )

        logger.info(f"ভার্টিক্যাল ভিডিও রেন্ডার সম্পন্ন: {out_video_path}")
        return out_video_path

    finally:
        # Cleanup temporary slide images
        for p in temp_files:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
