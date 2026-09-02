# 🚀 Social Autopilot: Automated Multi-Format Social Media Scheduler

> **100% Free, Zero Paid API Dependencies, Self-Hosted Multi-Format Social Media Scheduling & Auto-Posting System**  
> Optimized for macOS (Apple Silicon M1/M2/M3) and Linux.

---

## ✨ Features

- 🆓 **Zero Paid API Dependencies for Media**:
  - **Bengali Neural TTS**: Powered by Microsoft Edge Neural Voices (`bn-BD-PradeepNeural` / `bn-BD-NabanitaNeural`) with zero API costs.
  - **Dynamic Visual Design**: Automated high-contrast graphic card generation with Pillow.
  - **9:16 Vertical Video Renderer (Shorts/Reels)**: 1080x1920 portrait video rendering with MoviePy & FFmpeg synchronized with voiceover audio length.
- 🧠 **AI Content Engine**:
  - Generates high-retention social captions in native Bengali script (`bn-BD`), hashtags, vertical narration voiceovers, and takeaway cards.
  - Seamless fallback mode: operates offline/in test mode without crashing even if the API key is missing.
- 📅 **Reliable Task Scheduling**:
  - CSV-driven job queue (`schedule.csv`) tracking `id,publish_time,topic_title,keywords_hashtags,content_type,platforms,status,error_log`.
  - Driven by `APScheduler` background daemon with atomic state transitions (`pending` ➔ `processing` ➔ `posted` / `posted (dry-run)`).
- 🌐 **Multi-Platform Publishing & Resilient Dry-Run**:
  - Direct REST integration with **Meta Graph API** (Facebook Page text, photo, and video) and **LinkedIn REST API** (UGC text & media).
  - **Automatic Dry-Run Fallback**: If API keys are missing or network calls fail, outputs are neatly archived in timestamped directories under `output/dry_run_*` containing `caption.txt`, `meta.json`, and rendered media files.
- 🖥️ **CLI Management**:
  - Easily run the daemon, test individual post types, list queued tasks, or add new schedules directly from terminal.

---

## 🛠️ System Requirements

- **Operating System**: macOS (Apple Silicon M1/M2/M3 or Intel) or Linux (Ubuntu/Debian/RHEL)
- **Python**: 3.11 or newer
- **FFmpeg**:
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`
- **Bengali Fonts**:
  - macOS: Built-in system fonts (`Kohinoor Bangla`, `Bangla Sangam MN`, `kalpurush`, `Siyamrupali`).
  - Linux: Install fonts via:
    ```bash
    sudo apt-get install fonts-kalpurush fonts-noto-core
    ```

---

## 📦 Installation & Setup

1. **Clone or Navigate to the Project Folder**:
   ```bash
   cd social-autopilot
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and configure your keys:
   ```ini
   # Google Gemini API
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash

   # Meta Graph API (Facebook Page & Instagram)
   META_PAGE_ID=
   META_ACCESS_TOKEN=
   INSTAGRAM_ACCOUNT_ID=

   # LinkedIn REST API
   LINKEDIN_AUTHOR_URN=
   LINKEDIN_ACCESS_TOKEN=

   # Voiceover Voice (bn-BD-PradeepNeural or bn-BD-NabanitaNeural)
   DEFAULT_TTS_VOICE=bn-BD-PradeepNeural
   ```
   *(Note: If API keys are empty, Social Autopilot automatically operates in Dry-Run mode and saves all rendered media locally).*

---

## 💻 CLI Usage

The system includes a CLI (`cli.py`) for management, manual runs, and daemon execution:

### 1. View Scheduled Queue
```bash
python cli.py list
```

### 2. Add a New Scheduled Post
```bash
# Add a 9:16 vertical video post
python cli.py add \
  --title "গার্মেন্টস লাইনে কোয়ালিটি কন্ট্রোল" \
  --type video \
  --time "2026-09-03 14:30" \
  --keywords "#QC #Garments #Apparel" \
  --platforms "facebook,linkedin"

# Add an image card post
python cli.py add \
  --title "পোশাক শিল্পে 5S বাস্তবায়ন" \
  --type image \
  --time "2026-09-03 18:00" \
  --keywords "#Lean #Manufacturing"
```

### 3. Instant Live Publishing (`publish-now` / `generate-and-publish`)
তাৎক্ষণিকভাবে সক্রিয় পার্সোনা অনুযায়ী নতুন কনটেন্ট তৈরি করে সরাসরি লিঙ্কডইনে লাইভ পাবলিশ করতে:
```bash
# ১. ব্যক্তিগত প্রোফাইল থেকে তাৎক্ষণিক টেক্সট পোস্ট লাইভ পাবলিশ:
ENV_FILE=.env.personal python cli.py publish-now --type text_only

# ২. কোম্পানি পেজ থেকে তাৎক্ষণিক টেক্সট পোস্ট লাইভ পাবলিশ:
ENV_FILE=.env.company python cli.py publish-now --type text_only

# ৩. কাস্টম টাইটেল ও ইমেজ কার্ড দিয়ে সরাসরি লাইভ পোস্ট:
ENV_FILE=.env.personal python cli.py publish-now \
  --title "গার্মেন্টস লাইনে ব্যালেন্সিং টেকনিক" \
  --type image \
  --keywords "#LineBalancing #IndustrialEngineering"
```

### 4. Test Run (Dry-Run Generator)
Instantly generate media and test the pipeline without publishing live:
```bash
# Test 1080x1080 image card generation
python cli.py test-dry-run image

# Test 9:16 vertical video (Shorts/Reels) generation
python cli.py test-dry-run video

# Test analytical text post
python cli.py test-dry-run text_only
```

### 5. Process Pending Queue Immediately
```bash
python cli.py process-now
```

### 6. Start the Background Scheduler Daemon
```bash
python cli.py run --interval 60
```

---

## 🤖 Running as a Background Daemon

### Option A: Using `nohup` (Simple Background Run)
```bash
source venv/bin/activate
nohup python cli.py run > autopilot.stdout 2>&1 &
echo $! > autopilot.pid
```
To stop the daemon:
```bash
kill $(cat autopilot.pid) && rm autopilot.pid
```

### Option B: macOS `launchd` (Auto-start on Login)
Create `~/Library/LaunchAgents/com.autopilot.scheduler.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.autopilot.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Volumes/backup-software/Personal/social-autopilot/venv/bin/python</string>
        <string>/Volumes/backup-software/Personal/social-autopilot/cli.py</string>
        <string>run</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Volumes/backup-software/Personal/social-autopilot</string>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Volumes/backup-software/Personal/social-autopilot/autopilot.stdout</string>
    <key>StandardErrorPath</key>
    <string>/Volumes/backup-software/Personal/social-autopilot/autopilot.stderr</string>
</dict>
</plist>
```
Load the agent:
```bash
launchctl load ~/Library/LaunchAgents/com.autopilot.scheduler.plist
```

### Option C: Linux `systemd` Service
Create `/etc/systemd/system/social-autopilot.service`:
```ini
[Unit]
Description=Social Autopilot Background Scheduler
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/social-autopilot
ExecStart=/path/to/social-autopilot/venv/bin/python cli.py run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now social-autopilot
```

---

## 📁 Output Directory Structure

Generated posts and dry-run outputs are organized inside `output/`:

```
output/
├── dry_run_20260903_015500_101/
│   ├── caption.txt          # Native Bengali formatted caption with hashtags
│   ├── meta.json            # Task metadata, timestamp, target platforms
│   └── video_101.mp4        # Rendered 1080x1920 vertical video with synced voiceover
├── dry_run_20260903_015510_102/
│   ├── caption.txt
│   ├── meta.json
│   └── card_102.png         # Rendered 1080x1080 high-contrast Bengali infographic card
├── dry_run_20260903_015515_103/
│   ├── caption.txt
│   └── meta.json            # Analytical breakdown text post payload
├── autopilot.log            # Rolling logs with execution details
└── ...
```

---

## 🧪 Running Automated Tests

Run the automated test suite to verify Bengali typography, Edge TTS audio synthesis, MoviePy vertical video rendering, and dry-run publisher:

```bash
source venv/bin/activate
python test_pipeline.py
```
