# Raspberry Pi OS Deployment Guide

This app runs on FastAPI/uvicorn and works well on Raspberry Pi OS (Debian). Below are minimal steps.

## 1) Copy the project to your Pi
- Option A: Git clone (recommended)
- Option B: Zip and copy via SCP

```bash
# On Raspberry Pi terminal
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip
cd ~
git clone https://your-repo-url.git Sclaper_bot
cd Sclaper_bot
```

If copying manually, ensure the directory is at `/home/pi/Sclaper_bot`.

## 2) Create a virtual environment and install deps
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Notes:
- We removed stdlib modules from requirements (sqlite3, asyncio) to avoid pip errors.
- On older Pi models, pandas/numpy wheels may be slow to build. If it fails, you can comment them out temporarily; the app should still run without heavy analytics features.

## 3) Run the server manually (test)
```bash
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 4000 --workers 1
```
- Access from LAN: http://<pi-ip>:4000

## 4) Optional: systemd service
Create a service file so it starts on boot.

```bash
# Copy sample and edit paths/users if needed
sudo cp deploy/sclaper-bot.service.sample /etc/systemd/system/sclaper-bot.service
sudo nano /etc/systemd/system/sclaper-bot.service

# If using a virtualenv, change ExecStart to:
# ExecStart=/home/pi/Sclaper_bot/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 4000 --workers 1

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable sclaper-bot
sudo systemctl start sclaper-bot

# Check logs
sudo journalctl -u sclaper-bot -f
```

## 5) Firewall/router notes
- Ensure the device is accessible on your LAN (same Wi‑Fi, no AP isolation).
- If using ufw: `sudo ufw allow 4000/tcp`.

## 6) Update workflow
```bash
cd /home/pi/Sclaper_bot
source venv/bin/activate
git pull
pip install -r requirements.txt
sudo systemctl restart sclaper-bot # if using the service
```

## 7) Troubleshooting
- pandas/numpy build failures: try `pip install --no-binary=:all: pandas numpy` or comment them out.
- App won’t start: check `main.py` is set to host `0.0.0.0` and port `4000`.
- WS not updating: verify your Pi’s time is correct (`timedatectl`) and network is stable.
