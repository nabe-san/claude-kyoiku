// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 調べものログ - 週次バッチ
// 中継シートのpending行をClaude(Web検索ツール)で要約 → 週次メール送信
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function weeklyDigest() {
  Logger.log('=== 週次調べものログ 開始 ===');

  const apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    Logger.log('[ERROR] ANTHROPIC_API_KEY が未設定です。スクリプトのプロパティに登録してください。');
    return;
  }

  const sheet = getQueueSheet_();
  if (!sheet) return;

  const rows = getPendingRows_(sheet);
  Logger.log('未処理件数: ' + rows.length);

  if (rows.length === 0) {
    sendDigestEmail_([]);
    Logger.log('=== 週次調べものログ 完了（該当なし） ===');
    return;
  }

  // 同時実行対策：処理対象を先にまとめてprocessingへロック
  rows.forEach(function (row) {
    sheet.getRange(row.rowIndex, COL.STATUS + 1).setValue('processing');
  });
  SpreadsheetApp.flush();

  const entries = [];
  rows.forEach(function (row) {
    Logger.log('--- 処理中: ' + row.query + ' ---');
    const markdown = callClaudeWithWebSearch_(row.query, apiKey);
    if (markdown) {
      entries.push(markdown);
      sheet.getRange(row.rowIndex, COL.STATUS + 1).setValue('processed');
      Logger.log('[' + row.query + '] 完了 ✓');
    } else {
      sheet.getRange(row.rowIndex, COL.STATUS + 1).setValue('pending');
      sheet.getRange(row.rowIndex, COL.NOTE + 1).setValue('処理失敗（次回再試行）');
      Logger.log('[' + row.query + '] [ERROR] 失敗。次回再試行します。');
    }
  });

  sendDigestEmail_(entries);
  Logger.log('=== 週次調べものログ 完了（' + entries.length + '/' + rows.length + '件成功） ===');
}


// ============================================================
// Claude APIによる要約生成（Web検索ツール使用）
// ============================================================

function callClaudeWithWebSearch_(query, apiKey) {
  const payload = {
    model: CONFIG.CLAUDE_MODEL,
    max_tokens: 4096, // Claude Opus 5はデフォルトでthinkingが動くため、要約本文＋thinking分の余裕を持たせる
    output_config: { effort: 'medium' },
    tools: [{ type: 'web_search_20260209', name: 'web_search', max_uses: 3 }],
    messages: [{ role: 'user', content: buildPrompt_(query) }],
  };

  const retryDelays = [15000, 30000, 60000];

  for (let attempt = 0; attempt <= retryDelays.length; attempt++) {
    let res;
    try {
      res = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', {
        method: 'post',
        contentType: 'application/json',
        headers: {
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
        },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true,
      });
    } catch (e) {
      Logger.log('[Claude] 通信エラー: ' + e.message);
      if (attempt < retryDelays.length) { Utilities.sleep(retryDelays[attempt]); continue; }
      return null;
    }

    const code = res.getResponseCode();

    if (code === 200) {
      const json = JSON.parse(res.getContentText());
      if (json.stop_reason === 'refusal') {
        Logger.log('[Claude] refusalのためスキップ: ' + query);
        return null;
      }
      const text = (json.content || [])
        .filter(function (b) { return b.type === 'text'; })
        .map(function (b) { return b.text; })
        .join('\n')
        .trim();
      return text || null;
    }

    if (code === 429 || code === 529) {
      Logger.log('[Claude] ' + code + ' リトライ ' + (attempt + 1) + '/' + (retryDelays.length + 1));
      if (attempt < retryDelays.length) Utilities.sleep(retryDelays[attempt]);
    } else {
      Logger.log('[Claude] エラー ' + code + ': ' + res.getContentText().substring(0, 200));
      return null;
    }
  }

  Logger.log('[Claude] 最大リトライ回数に達しました: ' + query);
  return null;
}

function buildPrompt_(query) {
  return (
    'あなたは高校教員の読書メモを補助するアシスタントです。\n' +
    '次の語句・質問についてWeb検索を使って調べ、出典つきの要約を作成してください。\n\n' +
    '対象: ' + query + '\n\n' +
    'まず「人物・用語」か「経緯・説明」かを判定し、以下の形式で**Markdownそのまま**出力してください' +
    '（前後に余計な説明・前置きは付けない。この形式以外の文章を出力しない）。\n\n' +
    '## ' + query + '\n' +
    '**種別**: 人物 または 用語 または 経緯\n\n' +
    '（概要説明を3〜5文で。Google「AIによる概要」より詳しく、背景や意義まで踏み込む）\n\n' +
    '**主要事実**（人物・用語の場合の見出し）または **時系列**（経緯の場合の見出し）\n' +
    '- 項目1\n' +
    '- 項目2\n' +
    '- ...(3〜6項目)\n\n' +
    '**出典**: 実際に検索して確認したURL（複数ある場合は主要な1つ）'
  );
}


// ============================================================
// メール送信
// ============================================================

function sendDigestEmail_(entries) {
  const range = getWeekRange_();
  const subject = '今週の調べものログ（' + range.startStr + '〜' + range.endStr + '）';

  const frontmatter = [
    '---',
    'type: quick_lookup_digest',
    'week: ' + range.startStr + '〜' + range.endStr,
    'verified: false',
    '---',
    '',
  ].join('\n');

  const body = entries.length > 0
    ? frontmatter + entries.join('\n\n---\n\n')
    : frontmatter + '今週は該当なし';

  GmailApp.sendEmail(CONFIG.DIGEST_TO, subject, body);
  Logger.log('メール送信完了（' + entries.length + '件） 宛先: ' + CONFIG.DIGEST_TO);
}

function getWeekRange_() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6); // 直近7日間
  const fmt = function (d) { return Utilities.formatDate(d, 'Asia/Tokyo', 'yyyy-MM-dd'); };
  return { startStr: fmt(start), endStr: fmt(end) };
}


// ============================================================
// スプレッドシート操作
// ============================================================

function getQueueSheet_() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.QUEUE_SHEET_ID);
    const sheet = ss.getSheetByName(CONFIG.QUEUE_SHEET_NAME);
    if (!sheet) {
      Logger.log('[ERROR] シート「' + CONFIG.QUEUE_SHEET_NAME + '」が見つかりません');
      return null;
    }
    return sheet;
  } catch (e) {
    Logger.log('[ERROR] スプレッドシートにアクセスできません: ' + e.message);
    return null;
  }
}

function getPendingRows_(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  const data = sheet.getRange(2, 1, lastRow - 1, 4).getValues();
  const pending = [];

  data.forEach(function (row, i) {
    if (row[COL.STATUS] === 'pending') {
      pending.push({
        rowIndex: i + 2, // シートの行番号（1始まり、ヘッダー行を除く）
        query: String(row[COL.QUERY]),
      });
    }
  });

  return pending;
}


// ============================================================
// セットアップ・運用用関数
// ============================================================

// スプレッドシートにヘッダー行を作成する（初回セットアップ時に1度だけ実行）
function setupSheet() {
  const sheet = getQueueSheet_();
  if (!sheet) return;

  const headers = ['タイムスタンプ', 'クエリ', '状態', 'メモ'];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
  sheet.setFrozenRows(1);
  Logger.log('ヘッダー行を作成しました ✓');
}

// 週次トリガーを設定する（初回のみ手動で実行。毎週日曜20時）
function setupTrigger() {
  for (const t of ScriptApp.getProjectTriggers()) {
    if (t.getHandlerFunction() === 'weeklyDigest') ScriptApp.deleteTrigger(t);
  }
  ScriptApp.newTrigger('weeklyDigest')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(20)
    .create();
  Logger.log('毎週日曜20時のトリガーを設定しました ✓');
}

// 手動でweeklyDigestを実行するテスト用エントリーポイント
function testRun() {
  Logger.log('=== testRun 開始 ===');
  weeklyDigest();
  Logger.log('=== testRun 完了 ===');
}

// 設定値とアクセス権を確認する診断用関数
function checkConfig() {
  Logger.log('=== 設定確認 ===');
  Logger.log('QUEUE_SHEET_ID   : ' + CONFIG.QUEUE_SHEET_ID);
  Logger.log('QUEUE_SHEET_NAME : ' + CONFIG.QUEUE_SHEET_NAME);
  Logger.log('DIGEST_TO        : ' + CONFIG.DIGEST_TO);
  Logger.log('CLAUDE_MODEL     : ' + CONFIG.CLAUDE_MODEL);

  const apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  Logger.log('ANTHROPIC_API_KEY: ' + (apiKey ? '設定済み (' + apiKey.substring(0, 8) + '...)' : '[ERROR] 未設定'));

  const token = PropertiesService.getScriptProperties().getProperty('SHARED_TOKEN');
  Logger.log('SHARED_TOKEN     : ' + (token ? '設定済み' : '[ERROR] 未設定'));

  try {
    const ss = SpreadsheetApp.openById(CONFIG.QUEUE_SHEET_ID);
    const sheet = ss.getSheetByName(CONFIG.QUEUE_SHEET_NAME);
    Logger.log('スプレッドシート : "' + ss.getName() + '" / シート "' + (sheet ? sheet.getName() : '[ERROR] 見つからない') + '" ✓');
  } catch (e) {
    Logger.log('スプレッドシート : [ERROR] ' + e.message);
  }

  Logger.log('=== 設定確認 完了 ===');
}
