// Based on the official PortOne V2 and Culture Portal contracts (local only).
// __test routes control this local stand-in. Never deploy this mock.
const http = require('http');
http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://local');
  const send = (status, body, type = 'application/json') => { res.writeHead(status, { 'Content-Type': type }); res.end(type === 'application/json' ? JSON.stringify(body) : body); };
  const body = req.body || {};
  if (req.method === 'POST' && url.pathname === '/__test/reset') {
    await pm.state.set('culturepick.payments', {}); await pm.state.set('culturepick.mode', 'ok'); await pm.state.set('culturepick.cancels', 0);
    return send(200, { ok: true });
  }
  if (req.method === 'POST' && url.pathname === '/__test/payment') {
    const payments = (await pm.state.get('culturepick.payments')) || {}; payments[body.id] = body;
    await pm.state.set('culturepick.payments', payments); return send(200, { ok: true });
  }
  if (req.method === 'POST' && url.pathname === '/__test/mode') { await pm.state.set('culturepick.mode', body.mode); return send(200, { ok: true }); }
  if (req.method === 'GET' && url.pathname === '/__test/state') return send(200, { cancellations: (await pm.state.get('culturepick.cancels')) || 0 });
  const mode = await pm.state.get('culturepick.mode');
  if (mode === 'failure') return send(500, '<html>upstream failed</html>', 'text/html');
  if (mode === 'malformed') return send(200, '<html>not json</html>', 'text/html');
  const match = url.pathname.match(/^\/payments\/([^/]+)(\/cancel)?$/);
  if (match) {
    if (req.headers.authorization !== 'PortOne test-secret') return send(401, { type: 'UNAUTHORIZED' });
    const payments = (await pm.state.get('culturepick.payments')) || {};
    const payment = payments[decodeURIComponent(match[1])];
    if (!payment) return send(404, { type: 'PAYMENT_NOT_FOUND' });
    if (req.method === 'GET' && !match[2]) return send(200, payment);
    if (req.method === 'POST' && match[2]) {
      if (payment.status !== 'PAID' || body.currentCancellableAmount !== payment.amount.total || body.amount !== payment.amount.total || body.storeId !== payment.storeId) return send(409, { type: 'CANCELLABLE_AMOUNT_CONSISTENCY_BROKEN' });
      payment.status = 'CANCELLED'; payment.amount.cancelled = payment.amount.total; await pm.state.set('culturepick.payments', payments);
      const count = ((await pm.state.get('culturepick.cancels')) || 0) + 1; await pm.state.set('culturepick.cancels', count);
      return send(200, { cancellation: { id: `cancel-${count}`, status: 'SUCCEEDED', totalAmount: body.amount } });
    }
  }
  if (req.method === 'GET' && url.pathname === '/period') {
    if (url.searchParams.get('serviceKey') !== 'test-culture-key') return send(200, '<response><resultCode>30</resultCode></response>', 'application/xml');
    return send(200, '<response><msgBody><totalCount>1</totalCount><perforList><seq>mock-1</seq><title>Mock Exhibition</title><startDate>20261101</startDate><endDate>20261231</endDate><place>Mock Gallery</place><realmName>미술</realmName><area>서울</area><thumbnail>https://example.com/poster.jpg</thumbnail></perforList></msgBody></response>', 'application/xml');
  }
  if (req.method === 'GET' && url.pathname === '/detail') return send(200, '<response><msgBody><perforInfo><seq>mock-1</seq><price>무료</price><url>https://example.com/event</url><contents1>공개 API 수집 테스트 전시입니다.</contents1><placeAddr>서울 테스트 주소</placeAddr></perforInfo></msgBody></response>', 'application/xml');
  return send(501, { message: 'Endpoint not modelled by this local stand-in' });
}).listen(process.env.PORT || 4010, '127.0.0.1');
