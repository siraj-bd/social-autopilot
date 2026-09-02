import json
import shutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import settings, OUTPUT_DIR, logger


def dry_run_dump(task_id: str, payload: dict, media_path: Optional[Path] = None) -> Path:
    """Dumps post caption, metadata, and generated media to a timestamped folder in output/."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_folder = OUTPUT_DIR / f"dry_run_{timestamp}_{task_id}"
    dump_folder.mkdir(parents=True, exist_ok=True)

    # Save caption.txt
    caption_path = dump_folder / "caption.txt"
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(payload.get("caption", ""))

    # Save metadata JSON
    meta_path = dump_folder / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Copy media file if present
    if media_path and media_path.exists():
        destination = dump_folder / media_path.name
        shutil.copy(media_path, destination)
        logger.info(f"মিডিয়া ফাইল ড্রাফট ফোল্ডারে কপি করা হয়েছে: {destination.name}")

    logger.info(f"📁 [Dry-Run] পোস্ট ড্রাফট সফলভাবে সংরক্ষণ করা হয়েছে: {dump_folder}")
    return dump_folder


# ---------------------------------------------------------------------------
# Meta Graph API Handlers (Facebook Page / Instagram)
# ---------------------------------------------------------------------------

def publish_to_facebook_page(caption: str, content_type: str, media_path: Optional[Path] = None) -> dict:
    """Publishes text, photo, or video to a Facebook Page via Graph API."""
    if not settings.META_PAGE_ID or not settings.META_ACCESS_TOKEN:
        raise ValueError("META_PAGE_ID বা META_ACCESS_TOKEN অনুপস্থিত")

    base_url = f"https://graph.facebook.com/v19.0/{settings.META_PAGE_ID}"

    if content_type == "text_only" or not media_path:
        url = f"{base_url}/feed"
        payload = {"message": caption, "access_token": settings.META_ACCESS_TOKEN}
        resp = requests.post(url, data=payload, timeout=30)
    elif content_type == "image":
        url = f"{base_url}/photos"
        payload = {"caption": caption, "access_token": settings.META_ACCESS_TOKEN}
        with open(media_path, "rb") as f:
            resp = requests.post(url, data=payload, files={"source": f}, timeout=60)
    elif content_type == "video":
        url = f"{base_url}/videos"
        payload = {"description": caption, "access_token": settings.META_ACCESS_TOKEN}
        with open(media_path, "rb") as f:
            resp = requests.post(url, data=payload, files={"source": f}, timeout=120)
    else:
        raise ValueError(f"অপরিচিত content_type: {content_type}")

    resp_data = resp.json()
    if resp.status_code >= 400 or "error" in resp_data:
        raise RuntimeError(f"Facebook Graph API ত্রুটি: {resp_data}")

    logger.info(f"✅ Facebook-এ সফলভাবে পোস্ট হয়েছে! Post ID: {resp_data.get('id')}")
    return resp_data


# ---------------------------------------------------------------------------
# LinkedIn REST API Handlers
# ---------------------------------------------------------------------------

def is_valid_urn(urn: str) -> bool:
    """Validates that URN is not empty and does not contain placeholder text."""
    if not urn or "<" in urn or ">" in urn:
        return False
    return urn.startswith("urn:li:person:") or urn.startswith("urn:li:organization:")


def publish_to_linkedin(caption: str, content_type: str, media_path: Optional[Path] = None) -> dict:
    """Publishes text or media to LinkedIn via UGC / REST API."""
    if not settings.LINKEDIN_AUTHOR_URN or not settings.LINKEDIN_ACCESS_TOKEN:
        raise ValueError("LINKEDIN_AUTHOR_URN বা LINKEDIN_ACCESS_TOKEN অনুপস্থিত")

    if not is_valid_urn(settings.LINKEDIN_AUTHOR_URN):
        raise ValueError(
            f"অকার্যকর LINKEDIN_AUTHOR_URN ('{settings.LINKEDIN_AUTHOR_URN}')। "
            f"অনুগ্রহ করে .env ফাইলে প্লেসহোল্ডারের পরিবর্তে আপনার কোম্পানি পেজের আসল নিউমেরিক আইডি বসান (যেমন: urn:li:organization:12345678)"
        )

    headers = {
        "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    # For text-only post
    if content_type == "text_only" or not media_path:
        url = "https://api.linkedin.com/v2/ugcPosts"
        payload = {
            "author": settings.LINKEDIN_AUTHOR_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp_data = resp.json() if resp.text else {"status": resp.status_code}
        if resp.status_code >= 400:
            raise RuntimeError(f"LinkedIn API ত্রুটি: {resp_data}")
        post_id = resp_data.get("id", "")
        post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""
        logger.info(f"✅ LinkedIn-এ পোস্ট সফল হয়েছে! Post ID: {post_id}")
        if post_url:
            logger.info(f"🔗 LinkedIn Post URL: {post_url}")
        resp_data["post_url"] = post_url
        return resp_data

    # For Image/Video upload workflow
    upload_type = "image" if content_type == "image" else "video"
    recipe = "urn:li:digitalmediaRecipe:feedshare-image" if upload_type == "image" else "urn:li:digitalmediaRecipe:feedshare-video"

    # Step 1: Register Upload
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    register_payload = {
        "registerUploadRequest": {
            "recipes": [recipe],
            "owner": settings.LINKEDIN_AUTHOR_URN,
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
        }
    }
    reg_resp = requests.post(register_url, headers=headers, json=register_payload, timeout=30)
    reg_data = reg_resp.json()
    if reg_resp.status_code >= 400:
        raise RuntimeError(f"LinkedIn Asset Registration ব্যর্থ: {reg_data}")

    asset_urn = reg_data["value"]["asset"]
    upload_url = reg_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]

    # Step 2: Upload Media Binary
    with open(media_path, "rb") as f:
        up_resp = requests.put(upload_url, data=f, headers={"Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}"}, timeout=120)
    if up_resp.status_code >= 400:
        raise RuntimeError(f"LinkedIn Media Upload ব্যর্থ: {up_resp.status_code}")

    # Step 3: Create UGC Post with Media Asset
    post_url_endpoint = "https://api.linkedin.com/v2/ugcPosts"
    category = "IMAGE" if upload_type == "image" else "VIDEO"
    post_payload = {
        "author": settings.LINKEDIN_AUTHOR_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": caption},
                "shareMediaCategory": category,
                "media": [{
                    "status": "READY",
                    "description": {"text": caption[:200]},
                    "media": asset_urn,
                    "title": {"text": media_path.stem}
                }]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    resp = requests.post(post_url_endpoint, headers=headers, json=post_payload, timeout=30)
    resp_data = resp.json() if resp.text else {"status": resp.status_code}
    if resp.status_code >= 400:
        raise RuntimeError(f"LinkedIn Media Post প্রকাশ ব্যর্থ: {resp_data}")

    post_id = resp_data.get("id", "")
    post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""
    logger.info(f"✅ LinkedIn-এ মিডিয়া পোস্ট সফল হয়েছে! ID: {post_id}")
    if post_url:
        logger.info(f"🔗 LinkedIn Post URL: {post_url}")
    resp_data["post_url"] = post_url
    return resp_data


# ---------------------------------------------------------------------------
# Main Publisher Dispatcher with Automatic Dry-Run Fallback
# ---------------------------------------------------------------------------

def publish_post(
    task_id: str,
    content_type: str,
    caption: str,
    media_path: Optional[Path] = None,
    platforms: str = "facebook,linkedin",
    dry_run: bool = False
) -> tuple[bool, str]:
    """
    Publishes post to targeted platforms.
    If dry_run=True or credentials are missing/invalid, triggers Dry-Run Fallback Mode.
    Returns: (is_live_posted, message)
    """
    target_platforms = [p.strip().lower() for p in platforms.split(",") if p.strip()]

    payload = {
        "task_id": str(task_id),
        "content_type": content_type,
        "target_platforms": target_platforms,
        "caption": caption,
        "media_file": media_path.name if media_path else None,
        "created_at": datetime.now().isoformat()
    }

    # Explicit Dry-Run Mode: unconditionally bypass live API calls
    if dry_run:
        logger.info(f"🧪 [Dry-Run] টেস্ট মোড সক্রিয়। লাইভ এপিআই কল সম্পূর্ণ বন্ধ রেখে Task {task_id}-এর জন্য ড্রাফট ডাম্প হচ্ছে।")
        dump_dir = dry_run_dump(task_id, payload, media_path)
        return False, f"ড্রাফট সংরক্ষিত ({dump_dir.name})"

    has_meta = bool(settings.META_ACCESS_TOKEN and settings.META_PAGE_ID)
    has_linkedin = bool(settings.LINKEDIN_ACCESS_TOKEN and settings.LINKEDIN_AUTHOR_URN)

    # If neither platform has credentials configured, fallback directly to Dry-Run
    if not has_meta and not has_linkedin:
        logger.info(f"[Dry-Run] সোশ্যাল মিডিয়া ক্রেডেনশিয়াল অনুপস্থিত। Task {task_id}-এর জন্য অফলাইন ড্রাফট ডাম্প হচ্ছে।")
        dump_dir = dry_run_dump(task_id, payload, media_path)
        return False, f"ড্রাফট সংরক্ষিত ({dump_dir.name})"

    published_targets = []
    errors = []

    if "facebook" in target_platforms:
        if has_meta:
            try:
                res_fb = publish_to_facebook_page(caption, content_type, media_path)
                published_targets.append(f"Facebook (ID: {res_fb.get('id', 'OK')})")
            except Exception as e:
                logger.error(f"Facebook পাবলিশ ব্যর্থ: {e}")
                errors.append(f"Facebook: {e}")
        else:
            errors.append("Facebook credentials missing")

    if "linkedin" in target_platforms:
        if has_linkedin:
            try:
                res_li = publish_to_linkedin(caption, content_type, media_path)
                post_url = res_li.get("post_url", "")
                if post_url:
                    published_targets.append(f"LinkedIn ({post_url})")
                else:
                    published_targets.append(f"LinkedIn (ID: {res_li.get('id', 'OK')})")
            except Exception as e:
                logger.error(f"LinkedIn পাবলিশ ব্যর্থ: {e}")
                errors.append(f"LinkedIn: {e}")
        else:
            errors.append("LinkedIn credentials missing")

    if published_targets:
        success_msg = f"সফলভাবে পোস্ট হয়েছে: {', '.join(published_targets)}"
        if errors:
            success_msg += f" (সতর্কতা: {'; '.join(errors)})"
        return True, success_msg

    # If publishing failed on all intended channels, fallback to dry-run dump without crashing
    logger.warning(f"লাইভ পাবলিশিং সম্ভব হয়নি ({'; '.join(errors)})। ড্রাফট ডাম্প তৈরি হচ্ছে...")
    payload["errors"] = errors
    dump_dir = dry_run_dump(task_id, payload, media_path)
    return False, f"ড্রাফট সংরক্ষিত ({dump_dir.name})"
