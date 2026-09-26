# 🔍 HelpLens – AI-Powered Assistance for Everyday Problems

> **Snap, Describe & Fix in Minutes.** Simple, safety-first, step-by-step AI guidance for broken appliances, cryptic error codes, tricky DIY repairs, and confusing symbols.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Backend-Flask%203.0-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini%203.8%20Flash-orange.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Accessibility](https://img.shields.io/badge/A11y-WCAG%20AA%20Compliant-brightgreen.svg)]()

---

## 🌟 The Problem & The Solution

Every year, millions of functional household appliances are discarded, expensive emergency service call-outs are booked for 5-minute fixes, or dangerous DIY accidents occur simply because **error codes are cryptic**, **user manuals are lost**, and **online search results are flooded with generic ads**.

**HelpLens** transforms how anyone handles domestic glitches. Users snap a photo or describe their problem in plain English. HelpLens analyzes the issue with **Google Gemini Multimodal AI** and **OCR text extraction**, isolates the danger points, lists required household tools, and walks the user through an **interactive, checkable, audio-narrated step-by-step fix**.

---

## ✨ Key Features

- 📸 **Dual-Mode Multimodal Input:**
  - **Drag-and-Drop Photo Upload:** Upload photos of appliance stickers, leaks, dashboards, or broken items.
  - **Live Camera Snapshot:** Direct mobile and webcam photo capture via HTML5 WebRTC.
  - **Clipboard Image Paste:** Hit `Ctrl+V` anywhere on the page to paste a screenshot instantly!
  - **Plain Text Problem Prompt:** Type symptoms in everyday language.
- 🔤 **Smart OCR & Visual Symbol Decoding:**
  - Automatic extraction and recognition of error codes (e.g. Bosch E18, Samsung 4C, Whirlpool F21), car dashboard indicators, and ISO 3758 garment care symbols.
  - Automatic EXIF orientation correction and contrast enhancement via Pillow.
- 🛡️ **Safety-First Precaution Banner:**
  - Mandatory red/amber safety alerts for power isolation, water shutoffs, gas hazards, and personal protective equipment.
  - Clear **"When to Call a Professional"** thresholds to prevent dangerous mistakes.
- 🧰 **Interactive Checklist & Step Tracker:**
  - Clickable tools & materials pills to gather what you need before starting.
  - Interactive step cards with completion checkboxes and a real-time progress tracker (`3 of 5 Steps Done`).
- 🔊 **Hands-Free Text-to-Speech (TTS):**
  - Built-in accessible audio narration using the browser's Web Speech API. Listen to instructions while your hands are busy repairing!
- 💾 **Zero-Setup Local SQLite Database:**
  - Persistent history log of past solutions, searchable by symptom or error code.
  - 1-click solution bookmarking and helpfulness feedback (thumbs up / down).
- 🌓 **Modern, Accessible UI:**
  - Glassmorphic interface with automatic Light, Dark, and High-Contrast modes.
  - Mobile-first responsive design tailored for smartphones, tablets, and desktops.
  - Built-in `@media print` layout for printing physical repair guides or saving as PDF.
- ⚡ **Hackathon Smart Demo Mode:**
  - Works **out-of-the-box** even before entering a Gemini API key! High-fidelity realistic mock diagnostics ensure live presentations never fail due to Wi-Fi hiccups.
  - Instant live API Key switcher modal in the top navigation bar.

---

## 🏗️ System Architecture & Workflow

```
┌────────────────────────────────────────────────────────┐
│                      USER INPUT                        │
│   • Problem Text Description                           │
│   • Photo Upload / WebRTC Camera / Clipboard Paste     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             IMAGE PREPROCESSING & OCR                  │
│   • EXIF Auto-Orientation Correction (Pillow)          │
│   • Resolution Optimization (Max 1600px Lanczos)       │
│   • Contrast Enhancement & Optical Character Read      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               AI / LLM REASONING ENGINE                │
│   • Google Gemini 3.8 Flash (Interactions REST API)    │
│   • Safety Guardrail & Diagnosis Prompting             │
│   • Smart Heuristic Demo Fallback (Offline Mode)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            DATABASE & CACHING LAYER (SQLite)           │
│   • Stores Query History & AI Structured JSON          │
│   • Bookmarks & User Helpfulness Ratings               │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│           INTERACTIVE ASSISTANCE DASHBOARD             │
│   • Critical Safety Precautions Banner                 │
│   • Interactive Tools & Step Completion Tracker        │
│   • Text-to-Speech (TTS) Voice Narration               │
│   • Print / PDF Export & Copy to Clipboard             │
└────────────────────────────────────────────────────────┘
```

---

## 📁 Project Directory Structure

```
Help Lens/
├── app.py                     # Main Flask application & REST API routes
├── config.py                  # Environment & application configuration
├── database.py                # SQLite database helper (history, bookmarks, feedback)
├── ocr_service.py             # Image processing, EXIF normalization & OCR
├── ai_service.py              # Gemini AI client + Smart Demo fallback engine
├── test_app.py                # Automated unit and integration test suite
├── requirements.txt           # Python package dependencies
├── .env.example               # Template environment configuration
├── .env                       # Local environment file
├── .gitignore                 # Git ignore rules
├── run.bat                    # 1-Click launcher for Windows
├── run.sh                     # 1-Click launcher for macOS / Linux
├── README.md                  # Complete documentation & submission guide
├── uploads/                   # Temporary image storage (.gitkeep)
├── static/
│   ├── css/
│   │   └── style.css          # Responsive glassmorphic design system
│   ├── js/
│   │   └── app.js             # Reactive vanilla JS, Web Speech TTS, camera logic
│   └── images/
│       └── logo.svg           # HelpLens brand vector logo
└── templates/
    └── index.html             # Single-page modern accessible dashboard
```

---

## 🚀 Quickstart Guide

### Option 1: 1-Click Launcher (Fastest)

- **On Windows:** Double-click or run `run.bat` in Command Prompt / PowerShell.
- **On macOS / Linux:** Make executable and run:
  ```bash
  chmod +x run.sh
  ./run.sh
  ```

### Option 2: Manual Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/helplens.git
   cd helplens
   ```

2. **Create and activate a Python virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your environment:**
   ```bash
   cp .env.example .env
   ```
   *(Optional)* Open `.env` and insert your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.8-flash
   ```

5. **Start the application:**
   ```bash
   python app.py
   ```

6. Open your browser and navigate to: **`http://localhost:5000`**

---

## 🔑 Obtaining a Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **"Get API key"** and create a new free tier key.
4. Either paste the key into your `.env` file (`GEMINI_API_KEY=AIzaSy...`) **OR** click the **API Status Pill** in the HelpLens top navigation bar to enter it directly from the browser!

> 💡 **Hackathon Note:** If no API key is entered, HelpLens automatically runs in **Smart Demo Mode**. You can click any of the example chips (*Washer Error E18*, *Dripping Faucet*, *Router Red Light*, etc.) to test realistic full-fidelity diagnoses without any setup!

---

## 🧪 Running Automated Tests

HelpLens includes a test suite covering the health check, OCR handling, AI schema validation, mock fallbacks, and SQLite database operations:

```bash
python test_app.py
```

Expected output:
```
Ran 7 tests in 0.569s
OK
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `GET /` | `GET` | Renders the HelpLens Single-Page Dashboard |
| `GET /api/health` | `GET` | Returns system health, model status, and OCR engine state |
| `POST /api/analyze` | `POST` | Primary diagnosis endpoint. Accepts `problem_text`, `image` file, `category`, `urgency`, and `custom_api_key` |
| `POST /api/ocr` | `POST` | Standalone OCR text preview from uploaded image |
| `GET /api/history` | `GET` | Paginated query history with search & category filters |
| `GET /api/history/<id>` | `GET` | Detailed record of a specific previous fix |
| `POST /api/history/<id>/bookmark` | `POST` | Toggles bookmark state (0 / 1) for a record |
| `POST /api/history/<id>/feedback` | `POST` | Submits helpfulness rating (`rating: 1` or `-1`) |
| `DELETE /api/history/<id>` | `DELETE` | Deletes a specific history record |
| `DELETE /api/history` | `DELETE` | Clears all diagnostic history |

---

## 🌐 Cloud Deployment Guide

### Deploying to Render.com
1. Create a new **Web Service** on Render and connect your GitHub repository.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. In **Environment Variables**, set:
   - `GEMINI_API_KEY` = your Gemini API key
   - `PYTHON_VERSION` = `3.10.12` or higher

### Deploying to Railway.app
1. Click **New Project** → **Deploy from GitHub repo**.
2. Railway detects Python automatically.
3. Add variable `GEMINI_API_KEY` in settings.
4. Railway assigns an HTTPS domain automatically.

### Deploying via Docker / Google Cloud Run
A simple `Dockerfile` template:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
EXPOSE 8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

---

## 🏆 Hackathon Presentation & Live Demo Script

When presenting HelpLens to judges:
1. **Introduction (15s):** "Most people don't know what error code E18 means on their washing machine or how to fix a dripping tap, so they panic or spend $150 on an unnecessary call-out. Meet **HelpLens**."
2. **Demo 1 - Instant Example (30s):** Click the **"Washer Error E18"** chip. Hit **"Get AI Solution"**. Point out the **Safety Warning** (unplug power, scalding water hazard), the **Tools Checklist**, and the **interactive step completion tracker**.
3. **Demo 2 - Accessibility & Audio (20s):** Click the **"Listen"** button to showcase real-time hands-free Text-to-Speech narration while working.
4. **Demo 3 - Visual / Camera Capture (20s):** Drag and drop a photo or click **"Use Camera"** to take a live photo of any household item. Showcase the **OCR preview**.
5. **Demo 4 - History & Bookmarking (15s):** Click the **"History & Saved"** tab to show that past fixes are stored locally, searchable, and bookmarkable.
6. **Closing (10s):** Highlight the zero-dependency setup, Gemini 3.8 Flash grounding, and safety-first design philosophy.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
