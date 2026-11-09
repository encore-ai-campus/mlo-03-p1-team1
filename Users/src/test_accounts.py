"""Local-only synthetic login credentials for the generated test personas."""
import json
import secrets
import string
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERSONA_DIR = ROOT / "personas"
ACCOUNT_FILE = ROOT / "runs" / "test_accounts.json"


def _new_password():
    alphabet = string.ascii_letters + string.digits + "!@#$%_-"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(22))
        if (any(c.islower() for c in value) and any(c.isupper() for c in value)
                and any(c.isdigit() for c in value) and any(c in "!@#$%_-" for c in value)):
            return value


def ensure_test_accounts():
    """Create missing random credentials once; never rotate existing passwords."""
    ACCOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        accounts = json.loads(ACCOUNT_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        accounts = {}
    domain = __import__("os").getenv("ODDINARY_TEST_EMAIL_DOMAIN", "aiready.p-e.kr").strip().lstrip("@").lower()
    # Earlier generated IDs used a reserved .test domain, rejected by the site's
    # actual registration endpoint. Keep their random local part and password.
    for account in accounts.values():
        if account["login_id"].endswith("@example.test"):
            local_part = account["login_id"].rsplit("@", 1)[0]
            account["login_id"] = f"{local_part}@{domain}"
    for path in sorted(PERSONA_DIR.glob("persona_[0-9][0-9][0-9].md")):
        persona_id = path.stem
        if persona_id in accounts:
            continue
        local_id = f"oddinary.{persona_id[-3:]}.{secrets.token_hex(5)}"
        accounts[persona_id] = {"login_id": f"{local_id}@{domain}", "password": _new_password()}
    ACCOUNT_FILE.write_text(json.dumps(accounts, ensure_ascii=False, indent=2), encoding="utf-8")
    return accounts


def get_test_account(persona_id):
    return ensure_test_accounts()[persona_id]


def mark_registered(persona_id):
    accounts = ensure_test_accounts()
    accounts[persona_id]["registered"] = True
    ACCOUNT_FILE.write_text(json.dumps(accounts, ensure_ascii=False, indent=2), encoding="utf-8")
