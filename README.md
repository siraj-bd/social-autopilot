# 🚀 Social Autopilot: Automated Multi-Format Social Media Scheduler

> **100% Free, Zero Paid API Dependencies, Self-Hosted Multi-Format Social Media Scheduling & Auto-Posting System**  
> Optimized for macOS (Apple Silicon M1/M2/M3) and Linux.

---

## ✨ Features

- 🌐 **English Default & Multilingual Engine**:
  - **English Default Mode**: Generates authoritative, industry-tailored English posts by default (`DEFAULT_LANGUAGE=en`).
  - **Optional Bengali Mode**: Explicitly selectable (`--lang bn` / `language=bn`), preserving essential RMG, IE, SAM, 5S, AQL, and SOP technical terms in English.
  - **Neural TTS Voice Switching**: `en-US-ChristopherNeural` for English and `bn-BD-PradeepNeural` for Bengali.
- 📝 **Exact Custom Text Preservation**:
  - User-provided captions (`--caption`) bypass AI generation completely and are published verbatim with zero destructive truncation.
- 🎯 **Multi-Account Platform Architecture**:
  - Independent ON/OFF toggles for **LinkedIn Personal Profile**, **LinkedIn Company Page**, **Facebook Page**, and **Instagram Business**.
  - **Platform-Specific Adaptations**: Tailored hooks and character limits for each platform (LinkedIn 3,000, Facebook 63,206, Instagram 2,200 chars).
- 🖼️ **Single-Asset Media Reuse**:
  - Generates 1 validated 1080x1080 Image Card or 1080x1920 9:16 Vertical Video per task and reuses it across all targeted channels.
- 📅 **Industrial Scheduler Engine**:
  - CSV queue (`schedule.csv`) supporting one-time and recurring (`daily`, `weekly`, `hourly`) schedules.
  - Timezone-safe execution, automatic stale `processing` lock recovery, missed-task recovery, and atomic persistence.
- 🔒 **Secure & Self-Hosted**:
  - Zero hardcoded credentials, full environment isolation, and graceful dry-run fallbacks.

---

## 🛠️ System Requirements

- **Operating System**: macOS (Apple Silicon M1/M2/M3 or Intel) or Linux (Ubuntu/Debian/RHEL)
- **Python**: 3.11 or newer
- **FFmpeg**:
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`
- **Fonts**:
  - macOS: Built-in system fonts (`Kohinoor Bangla`, `Bangla Sangam MN`, `kalpurush`, `Siyamrupali`, `Arial`).
  - Linux: `sudo apt-get install fonts-kalpurush fonts-noto-core`

---

## 📦 Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/siraj-bd/social-autopilot.git
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
   ```bash
   cp .env.example .env
   ```
   Configure your keys in `.env` (or `.env.personal` / `.env.company`):
   ```ini
   # System Default Language (en = English, bn = Bengali)
   DEFAULT_LANGUAGE=en

   # Google Gemini API
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=gemini-3.6-flash

   # LinkedIn REST API
   LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_URN
   LINKEDIN_ACCESS_TOKEN=your_token

   # Meta Graph API (Facebook Page & Instagram)
   META_PAGE_ID=
   META_ACCESS_TOKEN=
   INSTAGRAM_ACCOUNT_ID=
   ```

---

## 💻 CLI Usage

### 1. Instant Live Publishing (`publish-now`)
```bash
# English Default Live Post to LinkedIn
ENV_FILE=.env.personal python cli.py publish-now --type text_only --lang en

# Optional Bengali Live Post with Preserved Technical Terms
ENV_FILE=.env.personal python cli.py publish-now --type text_only --lang bn

# Publish with Exact Custom Text (bypasses AI rewrite)
ENV_FILE=.env.personal python cli.py publish-now \
  --caption "Standardized method study is the foundation of apparel line balancing." \
  --platforms "linkedin,facebook" \
  --type text_only
```

### 2. View Scheduled Tasks
```bash
python cli.py list
```

### 3. Add Scheduled Tasks
```bash
# Add a recurring daily English video post
python cli.py add \
  --title "Garments Line Balancing & SAM Optimization" \
  --type video \
  --lang en \
  --time "2026-09-03 14:00" \
  --recurrence daily \
  --platforms "linkedin,facebook"
```

### 4. Run the Background Scheduler Daemon
```bash
python cli.py run --interval 60
```

### 5. Automated Test Suite
```bash
python test_pipeline.py
```

---

## 📄 License & Status

For detailed project status, architectural audits, and platform activation instructions, see [PROJECT_STATUS.md](PROJECT_STATUS.md).
