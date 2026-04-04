from pathlib import Path
import logging
import time
import requests
from config import Config

logger = logging.getLogger(__name__)
BASE_URL = "https://api.kie.ai/api/v1"


def _headers():
    return {
        "Authorization": f"Bearer {Config.kie_api_key}",
        "Content-Type": "application/json",
    }


def _download_file(url: str, output_path: Path) -> Path:
    logger.info("Downloading audio file | url=%s | dest=%s", url, output_path)
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                total_bytes += len(chunk)
    logger.info("Audio download complete | size_kb=%.1f | path=%s",
                total_bytes / 1024, output_path)
    return output_path


def _first_match(obj, wanted_keys):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in wanted_keys and value:
                return value
            found = _first_match(value, wanted_keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _first_match(item, wanted_keys)
            if found:
                return found
    return None


def generate_music(prompt: str, output_path: Path):
    if not Config.kie_api_key:
        raise RuntimeError(
            "KIE_API_KEY is missing in keys.env. "
            "Add it to keys.env: KIE_API_KEY=<your_key>"
        )

    payload = {
        "prompt": prompt,
        "customMode": False,
        "instrumental": True,
        "model": Config.kie_model,
        "callBackUrl": Config.kie_callback_url,
    }

    logger.info("Submitting music generation job to Kie.ai | model=%s", Config.kie_model)
    logger.debug("Music prompt: %s", prompt)

    try:
        r = requests.post(
            f"{BASE_URL}/generate",
            json=payload,
            headers=_headers(),
            timeout=120,
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Kie.ai generate HTTP request failed: %s", exc)
        raise

    data = r.json()
    logger.info("Kie.ai generate response | code=%s | body=%s", data.get("code"), data)

    if data.get("code") not in (200, 201):
        raise RuntimeError(f"Kie.ai generate request returned error code: {data}")

    task_id = _first_match(data, {"taskId", "id"})
    if not task_id:
        raise RuntimeError(
            f"Kie.ai response did not contain a taskId or id. Full response: {data}"
        )

    logger.info("Kie.ai job accepted | task_id=%s | will poll every %ds, timeout=%ds",
                task_id, Config.kie_poll_seconds, Config.kie_timeout_seconds)

    deadline = time.time() + Config.kie_timeout_seconds
    poll_count = 0

    while time.time() < deadline:
        poll_count += 1
        elapsed = int(time.time() - (deadline - Config.kie_timeout_seconds))

        try:
            s = requests.get(
                f"{BASE_URL}/generate/record-info",
                params={"taskId": task_id},
                headers=_headers(),
                timeout=120,
            )
            s.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Kie.ai poll #%d failed (will retry): %s", poll_count, exc)
            time.sleep(Config.kie_poll_seconds)
            continue

        status_data = s.json()
        status = str(_first_match(status_data, {"status", "state"}) or "").lower()

        logger.info("Kie.ai poll #%d | elapsed=%ds | status=%r | task_id=%s",
                    poll_count, elapsed, status, task_id)

        if status in {"complete", "completed", "success", "succeeded"}:
            audio_url = _first_match(status_data, {"audioUrl", "sourceAudioUrl"})
            if not audio_url:
                raise RuntimeError(
                    f"Kie.ai status={status!r} but no audioUrl found. "
                    f"Full response: {status_data}"
                )
            logger.info("Kie.ai music generation complete | audio_url=%s", audio_url)
            downloaded = _download_file(audio_url, output_path)
            return str(downloaded), {"task_id": task_id, "audio_url": audio_url}

        if status in {"error", "failed", "fail"}:
            raise RuntimeError(
                f"Kie.ai generation failed with status={status!r}. "
                f"Full response: {status_data}"
            )

        # Known in-progress statuses from Kie.ai API (intermediate states before completion)
        if status in {"pending", "processing", "queued", "running",
                      "text_success", "first_success", ""}:
            logger.info("Kie.ai still processing | status=%r | poll=%d | elapsed=%ds",
                        status, poll_count, elapsed)
        else:
            logger.warning(
                "Kie.ai returned unrecognised status %r — treating as in-progress. "
                "Full response: %s", status, status_data
            )

        time.sleep(Config.kie_poll_seconds)

    raise TimeoutError(
        f"Kie.ai music job timed out after {Config.kie_timeout_seconds}s "
        f"({poll_count} polls). Task ID: {task_id}"
    )
