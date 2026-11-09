import json, sqlite3, sys, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
if len(sys.argv) != 2:
    raise SystemExit("usage: process_page.py <page-json>")
source = Path(sys.argv[1])
if not source.is_absolute():
    source = (Path.cwd() / source).resolve()
payload = json.loads(source.read_text(encoding="utf-8"))
page = int(payload["page"])
records = payload["records"]
posters = ROOT / "posters"
posters.mkdir(parents=True, exist_ok=True)
db = sqlite3.connect(ROOT / "exhibitions.sqlite3")
db.execute("""
CREATE TABLE IF NOT EXISTS exhibitions (
  event_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  event_url TEXT,
  period TEXT,
  venue TEXT,
  venue_url TEXT,
  road_address TEXT,
  poster_url TEXT,
  poster_file TEXT,
  source_page INTEGER,
  crawled_at TEXT DEFAULT CURRENT_TIMESTAMP,
  poster_status TEXT
)
""")
outcomes = []
for row in records:
    event_id = row.get("event_id") or f"page{page}_{abs(hash(row.get('event_url','')))}"
    url = row.get("poster_url", "")
    ext = Path(urlparse(url).path).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    filename = f"p{page:03d}_{event_id}{ext}"
    target = posters / filename
    status = "missing_url" if not url else "downloaded"
    error = None
    if url:
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://search.naver.com/"})
            with urlopen(req, timeout=20) as response:
                content = response.read()
            if not content:
                raise ValueError("empty image response")
            target.write_bytes(content)
        except Exception as exc:
            status, error = "error", str(exc)
    db.execute("""
      INSERT INTO exhibitions(event_id,title,event_url,period,venue,venue_url,road_address,poster_url,poster_file,source_page,poster_status)
      VALUES(?,?,?,?,?,?,NULL,?,?,?,?)
      ON CONFLICT(event_id) DO UPDATE SET
        title=excluded.title,event_url=excluded.event_url,period=excluded.period,
        venue=excluded.venue,venue_url=excluded.venue_url,poster_url=excluded.poster_url,
        poster_file=excluded.poster_file,source_page=excluded.source_page,poster_status=excluded.poster_status
    """, (event_id,row.get("title",""),row.get("event_url"),row.get("period"),row.get("venue"),row.get("venue_url"),url,filename if status=="downloaded" else None,page,status))
    outcomes.append({"event_id":event_id,"title":row.get("title"),"poster_status":status,"poster_file":filename if status=="downloaded" else None,"error":error})
db.commit()
db.close()
result={"page":page,"records":len(records),"posters_saved":sum(x["poster_status"]=="downloaded" for x in outcomes),"failures":[x for x in outcomes if x["poster_status"]!="downloaded"],"folder":str(posters)}
(ROOT / "raw" / f"page_{page:03d}_result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
