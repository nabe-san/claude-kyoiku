// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 調べものログ - Web App（スマホからのPOSTを受け取り、中継シートに追記）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function doPost(e) {
  try {
    if (!e || !e.postData) {
      return jsonResponse_({ ok: false, error: 'no post data' });
    }

    const body = JSON.parse(e.postData.contents);
    const token = body.token;
    const query = String(body.query || '').trim();

    const expectedToken = PropertiesService.getScriptProperties().getProperty('SHARED_TOKEN');
    if (!expectedToken) {
      Logger.log('[doPost] [ERROR] SHARED_TOKEN が未設定です');
      return jsonResponse_({ ok: false, error: 'server not configured' });
    }
    if (token !== expectedToken) {
      return jsonResponse_({ ok: false, error: 'unauthorized' });
    }
    if (!query) {
      return jsonResponse_({ ok: false, error: 'empty query' });
    }

    appendToQueue_(query);
    return jsonResponse_({ ok: true });
  } catch (err) {
    Logger.log('[doPost] [ERROR] ' + err.message);
    return jsonResponse_({ ok: false, error: String(err) });
  }
}

function appendToQueue_(query) {
  const sheet = getQueueSheet_();
  if (!sheet) throw new Error('queue sheet not found');
  const now = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
  sheet.appendRow([now, query, 'pending', '']);
}

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
