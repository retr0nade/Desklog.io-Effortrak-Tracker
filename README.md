
# EfforTrak Screenshot Monitor


EfforTrak is an employee productivity monitoring application developed to capture and securely upload screenshots, track idle/active time, and operate discreetly in the system tray.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [License](#license)

---

## 📌 Overview

EfforTrak is designed to:

- Capture periodic screenshots during work hours  
- Detect and log idle vs. active time  
- Upload data securely to company servers  
- Operate silently in the background via the system tray

---

## ✅ Features

```bash
✔ Automatic Screenshot Capture
    └─ Configurable intervals (default: every 5 minutes)
    └─ Captures only when user is active

✔ Idle Time Detection
    └─ Tracks keyboard and mouse activity
    └─ Displays visual indicator for active/idle state

✔ Secure Cloud Upload
    └─ HTTPS encrypted transmission
    └─ Automatic retry on failure

✔ Discreet System Tray Operation
    └─ Runs silently in tray
    └─ Right-click menu with quick actions

✔ Multi-Platform Support
    └─ Compatible with Windows, macOS, and Linux
```

---

## 💻 System Requirements

```bash
Minimum:
  OS          : Windows 10/11, macOS 10.15+, Ubuntu 20.04+
  Python      : 3.8+
  RAM         : 2GB
  Disk Space  : 100MB

Recommended:
  OS          : Windows 11, macOS 12+
  Python      : 3.10+
  RAM         : 4GB
  Disk Space  : 200MB
```

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/effortrak.git
cd effortrak
```

### 2. Create a Virtual Environment (Recommended)

```bash
# On Linux/macOS:
python -m venv venv
source venv/bin/activate

# On Windows:
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

```ini
# .env (in project root)
EFFORTRAK_API_KEY=your_api_key_here
API_BASE_URL=https://tracker2.keylines.net
```

---

## 🔧 Configuration

### Environment Variables

```bash
EFFORTRAK_API_KEY=abc123xyz456      # Required - Your organization's API key
API_BASE_URL=https://tracker2.keylines.net  # Required - Base API endpoint
```

## 🚀 Usage

### Start the App

```bash
python main.py
```

### First-Time Setup

- Enter your **company URL** when prompted  
- Log in using **email/password** or **mobile OTP**

### System Tray Controls

```bash
Right-click Tray Icon:
├── Open       → Show application window
├── Start/Stop → Toggle screenshot capture
├── Logout     → Return to login screen
└── Exit       → Quit application
```

### Screenshot Storage

```bash
/screenshots/{user_id}_{timestamp}.jpg
```

---

## 🛠️ Troubleshooting

### Common Issues

#### ❌ Login Fails
```bash
✔ Check .env file for valid API key and URL
✔ Ensure internet connectivity
✔ Confirm API base URL is correct
```

#### ❌ Screenshots Not Capturing
```bash
✔ Is app in "Running" mode?
✔ Is user marked as idle?
✔ Check disk space availability
```

#### 🔥 High CPU Usage
```bash
✔ Increase screenshot interval
✔ Lower IMAGE_QUALITY in config.py
```

### Logs

```bash
logs/effortrak.log
```

---

## 🔐 Security

```bash
🔒 All transmissions use HTTPS
🔒 Screenshots are encrypted during upload
🔒 Local screenshots are stored encrypted
```

### 🕵️ Privacy

```bash
⏰ Captures only during 9 AM – 6 PM (work hours)
🔒 No screenshots during system lock
🚫 No keylogging of any kind
```

---

## 📄 License

```bash
This software is proprietary to:
→ Keyline DigiTech

Unauthorized use, modification, or redistribution is prohibited.

Contact IT Support:
📧 it-support@keylines.net
📞 Ext: 5555

Version       : 1.2.3
Last Updated  : 2025-06-17
```

