# Vibe Coding Sessions - v2

Safer first version:
- thumbnail provider configurable
- default thumbnail provider: local
- audio loop disabled by default
- Kie.ai polled for completion
- upload uses refresh token from keys.env

## Install
```bash
sudo apt update
sudo apt install python3-venv python3-full ffmpeg unzip -y

cd ~/Documents
rm -rf youtube_agent_v2
unzip youtube_agent_v2.zip -d ~/Documents
cd ~/Documents/youtube_agent_v2

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp keys.env.example keys.env
nano keys.env
```

Keep for first run:
THUMBNAIL_PROVIDER=local
LOOP_AUDIO=false
VIDEO_PRIVACY_STATUS=private

## Run
```bash
cd ~/Documents/youtube_agent_v2
source venv/bin/activate
python main.py
```

## Later
Set:
LOOP_AUDIO=true
THUMBNAIL_PROVIDER=pollinations
