import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import Config

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

_MAX_UPLOAD_CHUNKS = 500  # safety cap: ~500 chunks × default chunk = very large file limit


def _service():
    missing = [
        name for name, val in [
            ("YOUTUBE_CLIENT_ID", Config.youtube_client_id),
            ("YOUTUBE_CLIENT_SECRET", Config.youtube_client_secret),
            ("YOUTUBE_REFRESH_TOKEN", Config.youtube_refresh_token),
        ]
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"YouTube OAuth credentials incomplete in keys.env. Missing: {', '.join(missing)}"
        )

    logger.info("Refreshing YouTube OAuth token")
    creds = Credentials(
        token=None,
        refresh_token=Config.youtube_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=Config.youtube_client_id,
        client_secret=Config.youtube_client_secret,
        scopes=SCOPES,
    )
    try:
        creds.refresh(Request())
    except Exception as exc:
        logger.error("Failed to refresh YouTube OAuth token: %s", exc)
        raise RuntimeError(
            "YouTube token refresh failed. Check YOUTUBE_REFRESH_TOKEN, "
            "YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET in keys.env."
        ) from exc

    logger.info("YouTube OAuth token refreshed successfully")
    return build("youtube", "v3", credentials=creds)


def upload_video_and_thumbnail(video_path, thumbnail_path, title, description, tags):
    youtube = _service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags[:15],
            "categoryId": "10",  # Music
        },
        "status": {
            "privacyStatus": Config.video_privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    logger.info(
        "Starting YouTube upload | title=%r | privacy=%s | video_path=%s",
        title[:60], Config.video_privacy_status, video_path,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True),
    )

    response = None
    chunk_count = 0

    while response is None:
        chunk_count += 1
        if chunk_count > _MAX_UPLOAD_CHUNKS:
            raise RuntimeError(
                f"YouTube upload exceeded {_MAX_UPLOAD_CHUNKS} chunks without completing. "
                "The upload appears stuck. Check network stability and file size."
            )
        try:
            status, response = request.next_chunk()
            if status:
                progress_pct = int(status.progress() * 100)
                logger.info("Upload progress: %d%% | chunk=%d", progress_pct, chunk_count)
        except Exception as exc:
            logger.error("YouTube upload chunk #%d failed: %s", chunk_count, exc)
            raise

    video_id = response["id"]
    logger.info("Video uploaded successfully | video_id=%s | chunks=%d", video_id, chunk_count)

    logger.info("Setting thumbnail | video_id=%s | thumbnail=%s", video_id, thumbnail_path)
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path),
        ).execute()
        logger.info("Thumbnail set successfully | video_id=%s", video_id)
    except Exception as exc:
        # Thumbnail failure should not abort the pipeline — the video is already uploaded.
        logger.warning(
            "Thumbnail upload failed (video was uploaded successfully) | "
            "video_id=%s | error=%s", video_id, exc
        )

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    logger.info("Upload complete | url=%s", video_url)
    return {"video_id": video_id, "video_url": video_url}
