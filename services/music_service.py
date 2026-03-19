from pathlib import Path
import logging, time, requests
from config import Config
logger = logging.getLogger(__name__)
BASE_URL = "https://api.kie.ai/api/v1"

def _headers():
    return {"Authorization": f"Bearer {Config.kie_api_key}", "Content-Type": "application/json"}

def _download_file(url: str, output_path: Path) -> Path:
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
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
        raise RuntimeError("KIE_API_KEY is missing in keys.env")
    payload = {
        "prompt": prompt,
        "customMode": False,
        "instrumental": True,
        "model": Config.kie_model,
        "callBackUrl": Config.kie_callback_url,
    }
    logger.info("Submitting music generation job to Kie.ai")
    r = requests.post(f"{BASE_URL}/generate", json=payload, headers=_headers(), timeout=120)
    r.raise_for_status()
    data = r.json()
    logger.info("KIE GENERATE RESPONSE: %s", data)
    if data.get("code") not in (200, 201):
        raise RuntimeError(f"Kie.ai generate request failed: {data}")
    task_id = _first_match(data, {"taskId", "id"})
    if not task_id:
        raise RuntimeError(f"Kie.ai did not return taskId. Response: {data}")

    deadline = time.time() + Config.kie_timeout_seconds
    while time.time() < deadline:
        s = requests.get(f"{BASE_URL}/generate/record-info", params={"taskId": task_id}, headers=_headers(), timeout=120)
        s.raise_for_status()
        status_data = s.json()
        logger.info("KIE STATUS RESPONSE: %s", status_data)
        status = str(_first_match(status_data, {"status", "state"}) or "").lower()
        if status in {"complete", "completed", "success", "succeeded"}:
            audio_url = _first_match(status_data, {"audioUrl", "sourceAudioUrl"})
            if not audio_url:
                raise RuntimeError(f"Kie.ai completed but no audio URL was found. Response: {status_data}")
            downloaded = _download_file(audio_url, output_path)
            return str(downloaded), {"task_id": task_id, "audio_url": audio_url}
        if status in {"error", "failed", "fail"}:
            raise RuntimeError(f"Kie.ai generation failed. Response: {status_data}")
        time.sleep(Config.kie_poll_seconds)
    raise TimeoutError(f"Kie.ai job timed out after {Config.kie_timeout_seconds}s. Task ID: {task_id}")
