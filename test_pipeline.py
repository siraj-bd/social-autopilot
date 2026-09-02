import unittest
import shutil
from pathlib import Path
from mutagen.mp3 import MP3
from PIL import Image

from config import get_bengali_font_path, OUTPUT_DIR
from gemini_generator import generate_content
from media_engine import create_image_card, generate_voiceover, create_vertical_video
from publisher import publish_post, dry_run_dump, is_valid_urn
import scheduler


class TestSocialAutopilotPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        OUTPUT_DIR.mkdir(exist_ok=True)

    def test_01_font_detection(self):
        """Test Bengali font path detection."""
        font_path = get_bengali_font_path()
        self.assertTrue(bool(font_path), "Font path should not be empty")

    def test_02_gemini_generator_structure(self):
        """Test content generator outputs for video, image, and text_only formats."""
        for c_type in ["video", "image", "text_only"]:
            content = generate_content("গার্মেন্টস অটোমেশন টেকনিক", "#RMG #Tech", c_type)
            self.assertIn("caption", content)
            self.assertIn("voiceover", content)
            self.assertIn("slides", content)
            self.assertIn("badge", content)
            self.assertIn("bullets", content)
            self.assertGreater(len(content["caption"]), 10)

    def test_03_image_card_rendering(self):
        """Test 1080x1080 graphic card creation with Bengali typography."""
        card_path = create_image_card(
            title="পোশাক শিল্পে 5S বাস্তবায়ন",
            badge="লীন গাইড",
            bullets=["কাজের স্থান পরিচ্ছন্ন রাখা", "অপচয় শনাক্ত করা", "মান নিয়ন্ত্রণ নিশ্চিত করা"],
            filename="unit_test_card.png"
        )
        self.assertTrue(card_path.exists(), "Card image should exist")
        with Image.open(card_path) as img:
            self.assertEqual(img.size, (1080, 1080))
            self.assertEqual(img.format, "PNG")

    def test_04_voiceover_generation(self):
        """Test Edge TTS Bengali neural voiceover generation and duration."""
        test_text = "গার্মেন্টস লাইনে ব্যালেন্সিং টেকনিক নিয়ে সংক্ষিপ্ত টিপস।"
        audio_path = generate_voiceover(test_text, "unit_test_voice.mp3")
        self.assertTrue(audio_path.exists(), "Voiceover mp3 should exist")
        mp3 = MP3(str(audio_path))
        self.assertGreater(mp3.info.length, 1.0, "Audio duration should be > 1.0s")

    def test_05_vertical_video_rendering(self):
        """Test 1080x1920 9:16 vertical video rendering with slides and audio sync."""
        audio_path = OUTPUT_DIR / "unit_test_voice.mp3"
        if not audio_path.exists():
            audio_path = generate_voiceover("ভিডিও টেস্ট ভয়েসওভার।", "unit_test_voice.mp3")

        slides = ["১. সমস্যা চিহ্নিতকরণ", "২. সঠিক সমাধান", "৩. টেকসই ফলাফল"]
        video_path = create_vertical_video(
            title="স্মার্ট প্রোডাকশন গাইড",
            slides=slides,
            audio_path=audio_path,
            filename="unit_test_short.mp4"
        )
        self.assertTrue(video_path.exists(), "Vertical video should exist")

    def test_06_dry_run_dump_and_publisher(self):
        """Test Dry-Run publisher and live publishing status handling."""
        card_path = OUTPUT_DIR / "unit_test_card.png"
        payload = {
            "task_id": "UT_999",
            "content_type": "image",
            "caption": "টেস্ট সোশ্যাল মিডিয়া ক্যাপশন",
        }
        dump_folder = dry_run_dump("UT_999", payload, card_path)
        self.assertTrue(dump_folder.exists())
        self.assertTrue((dump_folder / "caption.txt").exists())
        self.assertTrue((dump_folder / "meta.json").exists())

        is_live, msg = publish_post(
            task_id="UT_999",
            content_type="image",
            caption="টেস্ট সোশ্যাল মিডিয়া ক্যাপশন",
            media_path=card_path,
            platforms="facebook,linkedin"
        )
        self.assertTrue(bool(msg))

    def test_07_custom_caption_preservation(self):
        """Test that exact user-provided text is preserved in dry run dump."""
        custom_text = "সম্পূর্ণ নির্দিষ্ট টেক্সট যা অপরিবর্তিত থাকবে।"
        payload = {
            "task_id": "UT_CUSTOM",
            "content_type": "text_only",
            "caption": custom_text
        }
        dump_folder = dry_run_dump("UT_CUSTOM", payload)
        saved_caption = (dump_folder / "caption.txt").read_text(encoding="utf-8")
        self.assertEqual(saved_caption.strip(), custom_text.strip())

    def test_08_recurrence_calculation(self):
        """Test daily, weekly, hourly recurrence calculation."""
        base_time = "2026-09-03 10:00"
        daily_next = scheduler.calculate_next_run(base_time, "daily")
        self.assertEqual(daily_next, "2026-09-04 10:00")

        weekly_next = scheduler.calculate_next_run(base_time, "weekly")
        self.assertEqual(weekly_next, "2026-09-10 10:00")

        hourly_next = scheduler.calculate_next_run(base_time, "hourly")
        self.assertEqual(hourly_next, "2026-09-03 11:00")

        none_next = scheduler.calculate_next_run(base_time, "none")
        self.assertEqual(none_next, "")

    def test_09_stale_lock_recovery(self):
        """Test recovery of tasks stuck in 'processing' status."""
        test_rows = [
            {"id": "991", "publish_time": "2026-09-03 01:00", "topic_title": "T1", "status": "processing"},
            {"id": "992", "publish_time": "2026-09-03 01:00", "topic_title": "T2", "status": "posted"}
        ]
        scheduler.write_tasks(test_rows)
        scheduler.recover_stale_processing_tasks()
        recovered_rows = scheduler.read_tasks()
        row_991 = next(r for r in recovered_rows if r.get("id") == "991")
        self.assertEqual(row_991.get("status"), "pending")

    def test_10_urn_validation(self):
        """Test URN validation helper."""
        self.assertTrue(is_valid_urn("urn:li:person:MQzC-zOANk"))
        self.assertTrue(is_valid_urn("urn:li:organization:12345678"))
        self.assertFalse(is_valid_urn("urn:li:organization:<আমার_কোম্পানি_পেজ_আইডি>"))
        self.assertFalse(is_valid_urn("<ID>"))
        self.assertFalse(is_valid_urn(""))


if __name__ == "__main__":
    unittest.main()
