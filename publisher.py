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


def get_linkedin_headers() -> dict:
    """Returns official required headers for modern LinkedIn REST API requests."""
    return {
        "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "LinkedIn-Version": settings.LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0"
    }


def _upload_linkedin_image(author_urn: str, image_path: Path) -> str:
    """
    Initializes upload and transfers image binary using modern LinkedIn Images REST API.
    Endpoint: POST https://api.linkedin.com/rest/images?action=initializeUpload
    Returns: urn:li:image:...
    """
    init_url = "https://api.linkedin.com/rest/images?action=initializeUpload"
    init_payload = {
        "initializeUploadRequest": {
            "owner": author_urn
        }
    }
    resp = requests.post(init_url, headers=get_linkedin_headers(), json=init_payload, timeout=30)
    resp_data = resp.json() if resp.text else {}
    if resp.status_code >= 400:
        if resp.status_code == 403 and "organization" in author_urn:
            raise RuntimeError(
                f"LinkedIn Company Page Image Init 403 Access Denied: {resp_data}। "
                f"নিশ্চিত করুন যে আপনার লিঙ্কডইন অ্যাপে 'w_organization_social' অনুমোদন রয়েছে এবং আপনি পেজের অ্যাডমিন।"
            )
        raise RuntimeError(f"LinkedIn Image InitializeUpload ব্যর্থ (HTTP {resp.status_code}): {resp_data}")

    upload_url = resp_data["value"]["uploadUrl"]
    image_urn = resp_data["value"]["image"]

    with open(image_path, "rb") as f:
        up_resp = requests.put(
            upload_url,
            data=f,
            headers={
                "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
                "Content-Type": "image/png"
            },
            timeout=120
        )
    if up_resp.status_code >= 400:
        raise RuntimeError(f"LinkedIn Image Binary Upload ব্যর্থ (HTTP {up_resp.status_code})")

    logger.info(f"✅ LinkedIn ইমেজ আপলোড সফল: {image_urn}")
    return image_urn


def _upload_linkedin_video(author_urn: str, video_path: Path) -> str:
    """
    Initializes, uploads chunks, and finalizes video using modern LinkedIn Videos REST API.
    Endpoints:
      - Init: POST https://api.linkedin.com/rest/videos?action=initializeUpload
      - Part PUT: PUT <uploadUrl>
      - Finalize: POST https://api.linkedin.com/rest/videos?action=finalizeUpload
    Returns: urn:li:video:...
    """
    file_size = video_path.stat().st_size
    init_url = "https://api.linkedin.com/rest/videos?action=initializeUpload"
    init_payload = {
        "initializeUploadRequest": {
            "owner": author_urn,
            "fileSizeBytes": file_size,
            "uploadCaptions": False,
            "uploadThumbnail": False
        }
    }
    resp = requests.post(init_url, headers=get_linkedin_headers(), json=init_payload, timeout=30)
    resp_data = resp.json() if resp.text else {}
    if resp.status_code >= 400:
        if resp.status_code == 403 and "organization" in author_urn:
            raise RuntimeError(
                f"LinkedIn Company Page Video Init 403 Access Denied: {resp_data}। "
                f"নিশ্চিত করুন যে আপনার লিঙ্কডইন অ্যাপে 'w_organization_social' অনুমোদন রয়েছে এবং আপনি পেজের অ্যাডমিন।"
            )
        raise RuntimeError(f"LinkedIn Video InitializeUpload ব্যর্থ (HTTP {resp.status_code}): {resp_data}")

    video_urn = resp_data["value"]["video"]
    upload_token = resp_data["value"].get("uploadToken", "")
    instructions = resp_data["value"]["uploadInstructions"]

    uploaded_part_ids = []
    with open(video_path, "rb") as f:
        for part in instructions:
            upload_url = part["uploadUrl"]
            first_byte = part["firstByte"]
            last_byte = part["lastByte"]
            part_size = last_byte - first_byte + 1
            f.seek(first_byte)
            chunk_data = f.read(part_size)

            up_resp = requests.put(
                upload_url,
                data=chunk_data,
                headers={
                    "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
                    "Content-Type": "application/octet-stream"
                },
                timeout=180
            )
            if up_resp.status_code >= 400:
                raise RuntimeError(f"LinkedIn Video Part Upload ব্যর্থ (HTTP {up_resp.status_code})")

            etag = up_resp.headers.get("ETag") or up_resp.headers.get("etag") or ""
            if etag:
                uploaded_part_ids.append(etag)

    # Finalize Upload
    finalize_url = "https://api.linkedin.com/rest/videos?action=finalizeUpload"
    finalize_payload = {
        "finalizeUploadRequest": {
            "video": video_urn,
            "uploadToken": upload_token,
            "uploadedPartIds": uploaded_part_ids
        }
    }
    fin_resp = requests.post(finalize_url, headers=get_linkedin_headers(), json=finalize_payload, timeout=30)
    if fin_resp.status_code >= 400:
        raise RuntimeError(f"LinkedIn Video Finalize ব্যর্থ (HTTP {fin_resp.status_code}): {fin_resp.text}")

    logger.info(f"✅ LinkedIn ভিডিও আপলোড ও ফাইনালাইজেশন সফল: {video_urn}")
    return video_urn


def _publish_to_linkedin_core(author_urn: str, caption: str, content_type: str, media_path: Optional[Path] = None, platform_key: str = "linkedin_personal") -> dict:
    """
    Publishes text, image, or video to LinkedIn Personal Profile or Company Page
    using the modern LinkedIn Posts REST API (POST https://api.linkedin.com/rest/posts).
    """
    if not author_urn or not settings.LINKEDIN_ACCESS_TOKEN:
        raise ValueError("LINKEDIN_AUTHOR_URN বা LINKEDIN_ACCESS_TOKEN অনুপস্থিত")

    if not is_valid_urn(author_urn):
        raise ValueError(
            f"LinkedIn URN কনফিগারেশন ত্রুটি ('{author_urn}')। "
            f"অনুগ্রহ করে .env ফাইলে আসল নিউমেরিক আইডি বসান (যেমন: urn:li:organization:12345678 বা urn:li:person:MQzC-zOANk)"
        )

    validate_character_limit(caption, platform_key)

    # Handle Media Uploads via modern REST endpoints
    content_obj = None
    if media_path and media_path.exists():
        if content_type == "image":
            image_urn = _upload_linkedin_image(author_urn, media_path)
            content_obj = {
                "media": {
                    "id": image_urn,
                    "title": media_path.stem
                }
            }
        elif content_type == "video":
            video_urn = _upload_linkedin_video(author_urn, media_path)
            content_obj = {
                "media": {
                    "id": video_urn,
                    "title": media_path.stem
                }
            }

    # Modern LinkedIn Posts API Payload Schema
    post_payload = {
        "author": author_urn,
        "commentary": caption,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }
    if content_obj:
        post_payload["content"] = content_obj

    posts_url = "https://api.linkedin.com/rest/posts"
    resp = requests.post(posts_url, headers=get_linkedin_headers(), json=post_payload, timeout=30)
    resp_data = resp.json() if resp.text else {}

    if resp.status_code >= 400:
        if resp.status_code == 403 and "organization" in author_urn:
            raise RuntimeError(
                f"LinkedIn Company Page 403 Access Denied: {resp_data}। "
                f"নিশ্চিত করুন যে আপনার লিঙ্কডইন অ্যাপে 'Community Management API' / 'w_organization_social' অনুমোদন রয়েছে এবং আপনি পেজটির অ্যাডমিন।"
            )
        raise RuntimeError(f"LinkedIn Posts API ত্রুটি (HTTP {resp.status_code}): {resp_data or resp.text}")

    # LinkedIn Posts API returns 201 Created with x-restli-id header containing the post URN (urn:li:share:... or urn:li:ugcPost:...)
    post_urn = resp.headers.get("x-restli-id") or resp.headers.get("x-linkedin-id") or resp_data.get("id", "")
    post_url = f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else ""

    logger.info(f"✅ LinkedIn ({author_urn})-এ পোস্ট সফল হয়েছে! Post URN: {post_urn}")
    if post_url:
        logger.info(f"🔗 LinkedIn Post URL: {post_url}")

    result = {
        "id": post_urn,
        "post_url": post_url,
        "status_code": resp.status_code
    }
    return result


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
