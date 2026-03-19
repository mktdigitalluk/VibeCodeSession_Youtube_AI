import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import Config
logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def _service():
    if not all([Config.youtube_client_id, Config.youtube_client_secret, Config.youtube_refresh_token]):
        raise RuntimeError("YouTube OAuth credentials are incomplete in keys.env")
    creds = Credentials(
        token=None,
        refresh_token=Config.youtube_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=Config.youtube_client_id,
        client_secret=Config.youtube_client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

def upload_video_and_thumbnail(video_path, thumbnail_path, title, description, tags):
    youtube = _service()
    body = {
        "snippet": {"title": title[:100], "description": description, "tags": tags[:15], "categoryId": "10"},
        "status": {"privacyStatus": Config.video_privacy_status, "selfDeclaredMadeForKids": False},
    }
    logger.info("Uploading video to YouTube")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True))
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
    return {"video_id": video_id, "video_url": f"https://www.youtube.com/watch?v={video_id}"}
