import unittest
import shutil
from pathlib import Path
from mutagen.mp3 import MP3
from PIL import Image

from config import get_bengali_font_path, OUTPUT_DIR, get_platform_registry, normalize_platform_keys, get_tts_voice
from gemini_generator import generate_content, build_platform_captions, get_fallback_content
from media_engine import create_image_card, generate_voiceover, create_vertical_video
from publisher import publish_post, dry_run_dump, is_valid_urn, validate_character_limit
import scheduler


class TestSocialAutopilotPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        OUTPUT_DIR.mkdir(exist_ok=True)

    def test_01_font_detection(self):
        """Test Bengali font path detection."""
        font_path = get_bengali_font_path()
        self.assertTrue(bool(font_path), "Font path should not be empty")

    def test_02_gemini_generator_structure_english_default(self):
        """Test default English content generator outputs."""
        for c_type in ["video", "image", "text_only"]:
            content = generate_content("Garments Line Balancing", "#RMG #IE", c_type, lang="en")
            self.assertIn("caption", content)
            self.assertIn("voiceover", content)
            self.assertIn("slides", content)
            self.assertIn("badge", content)
            self.assertIn("bullets", content)
            self.assertIn("platform_captions", content)
            self.assertGreater(len(content["caption"]), 10)

    def test_03_image_card_rendering_english_and_bengali(self):
        """Test 1080x1080 graphic card creation in both English and Bengali."""
        # English card
        en_card = create_image_card(
            title="5S Implementation in Apparel Manufacturing",
            badge="Lean Guide",
            bullets=["Clean workplace", "Eliminate waste", "Ensure quality"],
            filename="unit_test_card_en.png",
            lang="en"
        )
        self.assertTrue(en_card.exists())
        with Image.open(en_card) as img:
            self.assertEqual(img.size, (1080, 1080))

        # Bengali card
        bn_card = create_image_card(
            title="পোশাক শিল্পে 5S বাস্তবায়ন",
            badge="লীন গাইড",
            bullets=["কাজের স্থান পরিচ্ছন্ন রাখা", "অপচয় শনাক্ত করা", "মান নিয়ন্ত্রণ নিশ্চিত করা"],
            filename="unit_test_card_bn.png",
            lang="bn"
        )
        self.assertTrue(bn_card.exists())

    def test_04_voiceover_neural_tts_language_switching(self):
        """Test Edge TTS neural voice switching between English and Bengali."""
        self.assertEqual(get_tts_voice("bn"), "bn-BD-PradeepNeural")
        self.assertEqual(get_tts_voice("en"), "en-US-ChristopherNeural")

        # English voiceover
        en_audio = generate_voiceover("Line balancing optimization techniques.", "unit_test_voice_en.mp3", lang="en")
        self.assertTrue(en_audio.exists())
        mp3_en = MP3(str(en_audio))
        self.assertGreater(mp3_en.info.length, 1.0)

        # Bengali voiceover
        bn_audio = generate_voiceover("গার্মেন্টস লাইনে ব্যালেন্সিং টেকনিক।", "unit_test_voice_bn.mp3", lang="bn")
        self.assertTrue(bn_audio.exists())
        mp3_bn = MP3(str(bn_audio))
        self.assertGreater(mp3_bn.info.length, 1.0)

    def test_05_vertical_video_rendering_english(self):
        """Test 1080x1920 9:16 vertical video rendering in English."""
        audio_path = OUTPUT_DIR / "unit_test_voice_en.mp3"
        if not audio_path.exists():
            audio_path = generate_voiceover("Video test voiceover in English.", "unit_test_voice_en.mp3", lang="en")

        slides = ["1. Problem Identification", "2. Technical Solution", "3. Sustainable Results"]
        video_path = create_vertical_video(
            title="Smart Production Guide",
            slides=slides,
            audio_path=audio_path,
            filename="unit_test_short_en.mp4",
            lang="en"
        )
        self.assertTrue(video_path.exists())

    def test_06_dry_run_dump_and_publisher(self):
        """Test Dry-Run publisher and multi-account status handling."""
        card_path = OUTPUT_DIR / "unit_test_card_en.png"
        payload = {
            "task_id": "UT_999",
            "content_type": "image",
            "caption": "Test social media caption",
        }
        dump_folder = dry_run_dump("UT_999", payload, card_path)
        self.assertTrue(dump_folder.exists())
        self.assertTrue((dump_folder / "caption.txt").exists())
        self.assertTrue((dump_folder / "meta.json").exists())

        is_live, msg, per_res = publish_post(
            task_id="UT_999",
            content_type="image",
            caption="Test social media caption",
            media_path=card_path,
            platforms="facebook,linkedin",
            dry_run=True
        )
        self.assertFalse(is_live)
        self.assertIn("dry_run", str(per_res))

    def test_07_custom_caption_preservation_no_rewrite(self):
        """Test that exact user-provided text is preserved without translation or rewrite."""
        custom_en = "Exact custom English text preserved as is."
        payload_en = {"task_id": "UT_C1", "caption": custom_en}
        dump_folder_en = dry_run_dump("UT_C1", payload_en)
        saved_en = (dump_folder_en / "caption.txt").read_text(encoding="utf-8")
        self.assertEqual(saved_en.strip(), custom_en.strip())

        custom_bn = "সম্পূর্ণ নির্দিষ্ট বাংলা টেক্সট যা অপরিবর্তিত থাকবে।"
        payload_bn = {"task_id": "UT_C2", "caption": custom_bn}
        dump_folder_bn = dry_run_dump("UT_C2", payload_bn)
        saved_bn = (dump_folder_bn / "caption.txt").read_text(encoding="utf-8")
        self.assertEqual(saved_bn.strip(), custom_bn.strip())

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
            {"id": "991", "publish_time": "2026-09-03 01:00", "topic_title": "T1", "status": "processing", "language": "en"},
            {"id": "992", "publish_time": "2026-09-03 01:00", "topic_title": "T2", "status": "posted", "language": "en"}
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

    def test_11_multi_platform_adapted_captions_en_and_bn(self):
        """Test tailored captions generation for each platform in both English and Bengali."""
        # English
        res_en = build_platform_captions("Master body content in English.", "Line Balancing", "#RMG #IE", "personal", lang="en")
        self.assertIn("linkedin_personal", res_en)
        self.assertIn("facebook_page", res_en)
        self.assertIn("Manufacturing Leader Insights", res_en["linkedin_personal"])

        # Bengali
        res_bn = build_platform_captions("মাস্টার বডি টেক্সট।", "লাইন ব্যালেন্সিং", "#RMG #IE", "personal", lang="bn")
        self.assertIn("linkedin_personal", res_bn)
        self.assertIn("বাস্তবসম্মত টেকঅ্যাওয়ে", res_bn["linkedin_personal"])

    def test_12_character_limit_enforcement(self):
        """Test that exceeding character limits throws explicit validation error."""
        oversized_ig_caption = "A" * 2500  # IG limit is 2200
        with self.assertRaises(ValueError):
            validate_character_limit(oversized_ig_caption, "instagram")

        valid_ig_caption = "A" * 2000
        validate_character_limit(valid_ig_caption, "instagram")

    def test_13_platform_normalization_and_toggle(self):
        """Test platform alias resolution and ON/OFF handling."""
        keys = normalize_platform_keys("linkedin,facebook,instagram")
        self.assertIn("facebook_page", keys)
        self.assertIn("instagram", keys)

    def test_14_media_reuse_and_dry_run_multi_account(self):
        """Test that single media_path is reused and dry-run returns per-account statuses."""
        card_path = OUTPUT_DIR / "unit_test_card_en.png"
        captions = {
            "linkedin_personal": "LinkedIn specific text",
            "facebook_page": "Facebook specific text"
        }
        is_live, msg, per_res = publish_post(
            task_id="UT_MULTI",
            content_type="image",
            caption=captions,
            media_path=card_path,
            platforms="linkedin_personal,facebook_page",
            dry_run=True
        )
        self.assertFalse(is_live)
        self.assertEqual(per_res["linkedin_personal"]["status"], "dry_run")
        self.assertEqual(per_res["facebook_page"]["status"], "dry_run")

    def test_15_technical_terms_preservation_in_bengali_mode(self):
        """Test that technical terms (SAM, SMV, Line Balancing, etc.) remain in English in Bengali fallback."""
        fallback = get_fallback_content("লাইন ব্যালেন্সিং", "#RMG #IE", "text_only", "personal", lang="bn")
        caption = fallback["caption"]
        self.assertIn("Cycle Time", caption)
        self.assertIn("Pitch Time", caption)
        self.assertIn("SAM", caption)
        self.assertIn("Bottleneck", caption)
        self.assertIn("WIP", caption)
        self.assertIn("NVA", caption)


if __name__ == "__main__":
    unittest.main()
