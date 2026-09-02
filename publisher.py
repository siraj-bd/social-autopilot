import json
import shutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Union, Tuple, List
from config import settings, OUTPUT_DIR, logger, get_platform_registry, normalize_platform_keys


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
# Character Limit Pre-Validation
# ---------------------------------------------------------------------------

def validate_character_limit(caption: str, platform_key: str) -> None:
    """
    Validates that the caption strictly does not exceed the target platform limit.
    Fails fast if exceeded without silent destructive truncation.
    """
    registry = get_platform_registry()
    account_config = registry.get(platform_key)
    if not account_config:
        return

    max_chars = account_config.max_characters
    actual_len = len(caption)
    if actual_len > max_chars:
        raise ValueError(
            f"[{account_config.name}] ক্যারেক্টার লিমিট অতিক্রম করেছে! "
            f"অনুমোদিত: {max_chars} অক্ষর, বর্তমান ক্যাপশন: {actual_len} অক্ষর।"
        )


# ---------------------------------------------------------------------------
# Meta Graph API Handlers (Facebook Page / Instagram Business)
# ---------------------------------------------------------------------------

def publish_to_facebook_page(caption: str, content_type: str, media_path: Optional[Path] = None) -> dict:
    """Publishes text, photo, or video to a Facebook Page via Graph API v19.0."""
    if not settings.META_PAGE_ID or not settings.META_ACCESS_TOKEN:
        raise ValueError("META_PAGE_ID বা META_ACCESS_TOKEN অনুপস্থিত। .env ফাইলে কনফিগার করুন।")

    validate_character_limit(caption, "facebook_page")
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

    post_id = resp_data.get("id", "")
    logger.info(f"✅ Facebook Page-এ সফলভাবে পোস্ট হয়েছে! Post ID: {post_id}")
    resp_data["post_url"] = f"https://www.facebook.com/{post_id}" if post_id else ""
    return resp_data


def publish_to_instagram(caption: str, content_type: str, media_path: Optional[Path] = None) -> dict:
    """
    Publishes image or video (Reels) to Instagram Business account via Meta Graph API container workflow.
    Requires public URL or direct upload hosting.
    """
    if not settings.INSTAGRAM_ACCOUNT_ID or not settings.META_ACCESS_TOKEN:
        raise ValueError("INSTAGRAM_ACCOUNT_ID বা META_ACCESS_TOKEN অনুপস্থিত।")

    validate_character_limit(caption, "instagram")

    if content_type == "text_only" or not media_path:
        raise ValueError("Instagram টেক্সট-অনলি পোস্ট সাপোর্ট করে না। Image বা Video আবশ্যক।")

    # Note: Instagram Graph API container endpoint requires publicly accessible media_url or direct upload
    base_url = f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_ACCOUNT_ID}"
    logger.info(f"ℹ️ Instagram Business কন্টেইনার তৈরি শুরু: Account {settings.INSTAGRAM_ACCOUNT_ID}")

    # For local testing without public URL host, Instagram API expects hosted media URL
    raise NotImplementedError(
        "Instagram Graph API লোকাল ফাইল পাথের জন্য পাবলিক হোস্টেড মিডিয়া URL বা Graph Reshard আপলোড প্রত্যাশা করে। "
        "অনুগ্রহ করে পাবলিক মিডিয়া হোস্টিং URL কনফিগার করুন।"
    )


# ---------------------------------------------------------------------------
# LinkedIn REST API Handlers (Personal Profile vs Company Page)
# ---------------------------------------------------------------------------

def is_valid_urn(urn: str) -> bool:
    """Validates that URN is not empty and does not contain placeholder text."""
    if not urn or "<" in urn or ">" in urn:
        return False
    return urn.startswith("urn:li:person:") or urn.startswith("urn:li:organization:")


def _publish_to_linkedin_core(author_urn: str, caption: str, content_type: str, media_path: Optional[Path] = None, platform_key: str = "linkedin_personal") -> dict:
    """Core UGC Publisher for LinkedIn Personal Profile or Company Organization."""
    if not author_urn or not settings.LINKEDIN_ACCESS_TOKEN:
        raise ValueError("LINKEDIN_AUTHOR_URN বা LINKEDIN_ACCESS_TOKEN অনুপস্থিত")

    if not is_valid_urn(author_urn):
        raise ValueError(
            f"LinkedIn URN কনফিগারেশন ত্রুটি ('{author_urn}')। "
            f"অনুগ্রহ করে .env ফাইলে আসল নিউমেরিক আইডি বসান (যেমন: urn:li:organization:12345678 বা urn:li:person:MQzC-zOANk)"
        )

    validate_character_limit(caption, platform_key)

    headers = {
        "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    # For text-only post
    if content_type == "text_only" or not media_path:
        url = "https://api.linkedin.com/v2/ugcPosts"
        payload = {
            "author": author_urn,
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
            if resp.status_code == 403 and "organization" in author_urn:
                raise RuntimeError(
                    f"LinkedIn Company Page 403 Access Denied: {resp_data}। "
                    f"নিশ্চিত করুন যে আপনার লিঙ্কডইন অ্যাপে 'Community Management API' / 'w_organization_social' অনুমোদন রয়েছে এবং আপনি পেজটির অ্যাডমিন।"
                )
            raise RuntimeError(f"LinkedIn API ত্রুটি: {resp_data}")
        post_id = resp_data.get("id", "")
        post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""
        logger.info(f"✅ LinkedIn ({author_urn})-এ পোস্ট সফল হয়েছে! Post ID: {post_id}")
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
            "owner": author_urn,
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
        }
    }
    reg_resp = requests.post(register_url, headers=headers, json=register_payload, timeout=30)
    reg_data = reg_resp.json()
    if reg_resp.status_code >= 400:
        if reg_resp.status_code == 403 and "organization" in author_urn:
            raise RuntimeError(
                f"LinkedIn Company Page Asset Registration 403 Access Denied: {reg_data}। "
                f"নিশ্চিত করুন যে আপনার লিঙ্কডইন অ্যাপে 'w_organization_social' অনুমোদন রয়েছে।"
            )
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
        "author": author_urn,
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
        if resp.status_code == 403 and "organization" in author_urn:
            raise RuntimeError(
                f"LinkedIn Company Page Media Post 403 Access Denied: {resp_data}। "
                f"নিশ্চিত করুন যে আপনার লিঙ্কডইন অ্যাপে 'w_organization_social' অনুমোদন রয়েছে।"
            )
        raise RuntimeError(f"LinkedIn Media Post প্রকাশ ব্যর্থ: {resp_data}")

    post_id = resp_data.get("id", "")
    post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""
    logger.info(f"✅ LinkedIn ({author_urn})-এ মিডিয়া পোস্ট সফল হয়েছে! ID: {post_id}")
    if post_url:
        logger.info(f"🔗 LinkedIn Post URL: {post_url}")
    resp_data["post_url"] = post_url
    return resp_data


def publish_to_linkedin(caption: str, content_type: str, media_path: Optional[Path] = None) -> dict:
    """Dispatches to LinkedIn Personal or Company based on configured URN."""
    platform_key = "linkedin_company" if "organization" in settings.LINKEDIN_AUTHOR_URN else "linkedin_personal"
    return _publish_to_linkedin_core(settings.LINKEDIN_AUTHOR_URN, caption, content_type, media_path, platform_key)


# ---------------------------------------------------------------------------
# Multi-Account Unified Publisher Dispatcher
# ---------------------------------------------------------------------------

def publish_post(
    task_id: str,
    content_type: str,
    caption: Union[str, Dict[str, str]],
    media_path: Optional[Path] = None,
    platforms: str = "linkedin,facebook",
    dry_run: bool = False
) -> Tuple[bool, str, Dict[str, dict]]:
    """
    Publishes content to all targeted and enabled social accounts.
    Reuses the single generated media_path across all enabled accounts.
    Uses platform-tailored captions while validating character limits.
    Returns: (is_overall_success, summary_message, per_account_results)
    """
    registry = get_platform_registry()
    target_platform_keys = normalize_platform_keys(platforms)
    per_account_results = {}

    # Resolve caption map: supports single string or platform-specific dictionary
    if isinstance(caption, dict):
        caption_map = caption
        master_caption = caption.get("master") or caption.get("linkedin_personal") or next(iter(caption.values()), "")
    else:
        master_caption = str(caption)
        caption_map = {k: master_caption for k in registry.keys()}

    payload = {
        "task_id": str(task_id),
        "content_type": content_type,
        "target_platforms": target_platform_keys,
        "caption": master_caption,
        "media_file": media_path.name if media_path else None,
        "created_at": datetime.now().isoformat()
    }

    # Explicit Dry-Run Mode: unconditionally bypass live API calls
    if dry_run:
        logger.info(f"🧪 [Dry-Run] টেস্ট মোড সক্রিয়। লাইভ এপিআই কল সম্পূর্ণ বন্ধ রেখে Task {task_id}-এর জন্য ড্রাফট ডাম্প হচ্ছে।")
        dump_dir = dry_run_dump(task_id, payload, media_path)
        for key in target_platform_keys:
            per_account_results[key] = {"status": "dry_run", "folder": str(dump_dir.name)}
        return False, f"ড্রাফট সংরক্ষিত ({dump_dir.name})", per_account_results

    success_accounts = []
    error_accounts = []

    for platform_key in target_platform_keys:
        account_config = registry.get(platform_key)
        if not account_config:
            continue

        # Check Account ON/OFF Toggle
        if not account_config.enabled:
            logger.info(f"ℹ️ [{account_config.name}] নিষ্ক্রিয় (OFF) থাকায় কোনো এপিআই রিকোয়েস্ট পাঠানো হয়নি।")
            per_account_results[platform_key] = {"status": "skipped", "reason": "Account toggled OFF"}
            continue

        # Get tailored caption for this specific account
        account_caption = caption_map.get(platform_key, master_caption)

        try:
            # 1. Validate character limit before making API call
            validate_character_limit(account_caption, platform_key)

            # 2. Dispatch to specific account handler
            if platform_key == "linkedin_personal":
                res = _publish_to_linkedin_core(
                    author_urn=settings.LINKEDIN_AUTHOR_URN if "person" in settings.LINKEDIN_AUTHOR_URN else "",
                    caption=account_caption,
                    content_type=content_type,
                    media_path=media_path,
                    platform_key="linkedin_personal"
                )
                post_url = res.get("post_url", "")
                success_accounts.append(f"LinkedIn Personal ({post_url})")
                per_account_results[platform_key] = {"status": "posted", "post_id": res.get("id"), "post_url": post_url}

            elif platform_key == "linkedin_company":
                res = _publish_to_linkedin_core(
                    author_urn=settings.LINKEDIN_AUTHOR_URN if "organization" in settings.LINKEDIN_AUTHOR_URN else "",
                    caption=account_caption,
                    content_type=content_type,
                    media_path=media_path,
                    platform_key="linkedin_company"
                )
                post_url = res.get("post_url", "")
                success_accounts.append(f"LinkedIn Company ({post_url})")
                per_account_results[platform_key] = {"status": "posted", "post_id": res.get("id"), "post_url": post_url}

            elif platform_key == "facebook_page":
                res = publish_to_facebook_page(account_caption, content_type, media_path)
                post_url = res.get("post_url", "")
                success_accounts.append(f"Facebook Page ({post_url or res.get('id')})")
                per_account_results[platform_key] = {"status": "posted", "post_id": res.get("id"), "post_url": post_url}

            elif platform_key == "instagram":
                res = publish_to_instagram(account_caption, content_type, media_path)
                success_accounts.append(f"Instagram ({res.get('id')})")
                per_account_results[platform_key] = {"status": "posted", "post_id": res.get("id")}

        except Exception as e:
            logger.error(f"❌ [{account_config.name}] পাবলিশ ব্যর্থ: {e}")
            error_accounts.append(f"{account_config.name}: {e}")
            per_account_results[platform_key] = {"status": "failed", "error": str(e)}

    # Determine overall status
    if success_accounts:
        summary_msg = f"সফলভাবে পোস্ট হয়েছে: {', '.join(success_accounts)}"
        if error_accounts:
            summary_msg += f" | সতর্কতা: {'; '.join(error_accounts)}"
        return True, summary_msg, per_account_results

    # If all targeted accounts failed or skipped, fallback to dry-run dump without crashing
    logger.warning(f"কোনো অ্যাকাউন্টে লাইভ পাবলিশ সম্ভব হয়নি ({'; '.join(error_accounts)})। ড্রাফট ডাম্প তৈরি হচ্ছে...")
    payload["errors"] = error_accounts
    payload["per_account_results"] = per_account_results
    dump_dir = dry_run_dump(task_id, payload, media_path)
    return False, f"ড্রাফট সংরক্ষিত ({dump_dir.name})", per_account_results
