from io import StringIO
from pathlib import Path
from alembic import command
from alembic.config import Config

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    output = StringIO()
    config = Config(str(root / 'backend/alembic.ini'), output_buffer=output)
    command.upgrade(config, 'head', sql=True)
    (root / 'database/mariadb/schema.sql').write_text('-- REFERENCE ONLY: generated from Alembic; apply migrations instead.\n' + output.getvalue(), encoding='utf-8')
    print('Updated database/mariadb/schema.sql')
