import json
from pathlib import Path
from app.main import app

if __name__ == '__main__':
    destination = Path(__file__).resolve().parents[3] / 'docs' / 'openapi.json'
    destination.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Updated docs/openapi.json')
