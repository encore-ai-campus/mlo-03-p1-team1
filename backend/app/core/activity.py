"""Small, non-sensitive browser context shared by API event producers."""
import re
from uuid import UUID


def valid_page_path(value):
    return bool(re.fullmatch(
        r'/(?:explore|recommendations|bookmarks|history|contents/[1-9][0-9]*|mypage(?:/(?:bookmarks|history|preferences|payments))?|payment/result)?', value
    ))


def request_activity_context(request):
    result = {}
    for key, header in (('anonymous_id', 'x-activity-anonymous-id'), ('session_id', 'x-activity-session-id')):
        try:
            value = request.headers.get(header)
            if value:
                result[key] = str(UUID(value))
        except (ValueError, AttributeError):
            pass  # Malformed optional analytics context must not fail a purchase.
    path = request.headers.get('x-activity-page', '')
    if valid_page_path(path):
        result['page_path'] = path
    return result
