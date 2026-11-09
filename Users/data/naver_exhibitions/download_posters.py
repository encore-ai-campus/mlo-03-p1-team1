import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
import mimetypes

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "raw" / "pages_001_010.json"
POSTERS = ROOT / "posters"
POSTERS.mkdir(parents=True, exist_ok=True)

pages = json.loads(SOURCE.read_text(encoding="utf-8"))
records = [record for page in pages for record in page.get("records", [])]
results = []
for record in records:
    event_id = record.get("event_id") or "unknown"
    url = record.get("poster_url")
    if not url:
        results.append({"event_id": event_id, "status": "missing_url"})
        continue
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    target = POSTERS / f"{event_id}{suffix}"
    if target.exists() and target.stat().st_size:
        results.append({"event_id": event_id, "status": "already_present", "file": target.name, "bytes": target.stat().st_size})
        continue
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://search.naver.com/"})
        with urlopen(req, timeout=30) as response:
            content = response.read()
            mime = response.headers.get_content_type()
        if not content:
            raise ValueError("empty image response")
        target.write_bytes(content)
        results.append({"event_id": event_id, "status": "downloaded", "file": target.name, "bytes": len(content), "content_type": mime})
    except Exception as exc:
        results.append({"event_id": event_id, "status": "error", "error": str(exc), "url": url})

(ROOT / "poster_downloads_001_010.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"records": len(records), "downloaded": sum(r["status"] == "downloaded" for r in results), "already_present": sum(r["status"] == "already_present" for r in results), "errors": [r for r in results if r["status"] == "error"], "folder": str(POSTERS)}, ensure_ascii=False))
