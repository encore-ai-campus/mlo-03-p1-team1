-- Bookmarks by content (anonymous aggregates).
SELECT content_id, COUNT(*) AS bookmarks FROM bookmarks GROUP BY content_id ORDER BY bookmarks DESC;
-- Daily behaviour totals; no personal identifiers exported.
SELECT DATE(occurred_at) AS day_utc, event_type, COUNT(*) AS events
FROM behavior_events GROUP BY DATE(occurred_at), event_type;
-- Reconciliation candidates: retry PortOne GET before altering state.
SELECT payment_id, status, amount, created_at FROM orders
WHERE status = 'PENDING' AND created_at < UTC_TIMESTAMP() - INTERVAL 10 MINUTE;
