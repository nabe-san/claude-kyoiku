// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 一問一答カード 自動生成スクリプト（Google Apps Script）
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const INPUT_FOLDER_ID  = '1pqfFijsZf6waVLzCi7qTH7X7nLdzQuIU';
const OUTPUT_FOLDER_ID = '1b-F1WcHV2BhJN2YKIDN5tRP5ab6RwmhP';

// ─── メイン処理 ──────────────────────────────────

function checkAndProcess() {
  const apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    console.log('【エラー】ANTHROPIC_API_KEY が未設定です。スクリプトのプロパティに登録してください。');
    return;
  }

  const inputFolder  = DriveApp.getFolderById(INPUT_FOLDER_ID);
  const outputFolder = DriveApp.getFolderById(OUTPUT_FOLDER_ID);

  // 処理済みファイル名を収集（outputの既存ドキュメント名から判定）
  const processed = new Set();
  const outFiles = outputFolder.getFiles();
  while (outFiles.hasNext()) {
    processed.add(outFiles.next().getName());
  }

  // inputの画像を走査
  const inFiles = inputFolder.getFiles();
  while (inFiles.hasNext()) {
    const file = inFiles.next();
    const mime = file.getMimeType();
    if (mime !== 'image/jpeg' && mime !== 'image/png') continue;

    const baseName = file.getName().replace(/\.(jpg|jpeg|png)$/i, '');
    const docName  = `${baseName}　一問一答カード`;

    if (processed.has(docName)) continue;

    console.log(`[処理中] ${file.getName()}`);
    try {
      const cards = generateCards(file, apiKey);
      createDoc(cards, docName, baseName, outputFolder);
      console.log(`[完了] ${docName}（${cards.length}枚）`);
    } catch (e) {
      console.error(`[エラー] ${file.getName()}: ${e.message}`);
    }
  }
}

// ─── カード生成（Anthropic API呼び出し）──────────

function generateCards(file, apiKey) {
  const b64  = Utilities.base64Encode(file.getBlob().getBytes());
  const mime = file.getMimeType();

  const payload = {
    model: 'claude-sonnet-4-6',
    max_tokens: 4096,
    system: [
      'あなたは高校日本史・公共の授業用フラッシュカードを作成するAIです。',
      '提供された教科書の見開き画像から重要語句を空欄にした一問一答カードを生成します。',
      '',
      '【ルール】',
      '- 人名・地名・事件名・制度名・概念など重要語句を1つだけ空欄にする',
      '- 年号・西暦・生年・没年など「数字の年」を答えさせる問題は作らない',
      '- 空欄は「＿＿＿＿」と表記する',
      '- 答えは空欄に入る語句のみ（1〜6語程度）',
      '- 20〜30枚作成する（少なすぎても多すぎても不可）',
      '- 画像に写っている内容のみから出題する',
      '- JSONのみ出力（前後の説明文は不要）',
      '',
      '【出力形式】',
      '[',
      '  {"question": "○○は＿＿＿＿を制定した。", "answer": "大宝律令"},',
      '  {"question": "＿＿＿＿は奴国の王に金印を授けた。", "answer": "後漢の光武帝"}',
      ']'
    ].join('\n'),
    messages: [{
      role: 'user',
      content: [
        {
          type: 'image',
          source: { type: 'base64', media_type: mime, data: b64 }
        },
        {
          type: 'text',
          text: 'この教科書の画像から一問一答カードを20〜30枚生成してください。'
        }
      ]
    }]
  };

  const res = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', {
    method: 'post',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const json = JSON.parse(res.getContentText());
  if (json.error) throw new Error(json.error.message);

  const text  = json.content[0].text;
  const match = text.match(/\[[\s\S]*\]/);
  if (!match) throw new Error('JSONが見つかりませんでした: ' + text.slice(0, 200));
  return JSON.parse(match[0]);
}

// ─── Googleドキュメント作成 ───────────────────────

function createDoc(cards, docName, unitName, outputFolder) {
  const doc  = DocumentApp.create(docName);
  const body = doc.getBody();

  // タイトル
  const title = body.appendParagraph(`一問一答カード　${unitName}`);
  title.setHeading(DocumentApp.ParagraphHeading.HEADING1);
  title.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
  body.appendParagraph(`全${cards.length}問`).setFontSize(10);

  // 問題一覧
  const qTable = body.appendTable();
  const qHdr   = qTable.appendTableRow();
  const qH1    = qHdr.appendTableCell('問題');
  qH1.setBackgroundColor('#0D2137');
  qH1.getChild(0).asText().setForegroundColor('#FFFFFF').setBold(true);

  cards.forEach((card, i) => {
    const row = qTable.appendTableRow();
    row.appendTableCell(`${i + 1}．${card.question}`)
       .getChild(0).asText().setForegroundColor('#000000');
  });

  // 解答（末尾にまとめて）
  body.appendParagraph('').setSpacingBefore(16);
  const ap = body.appendParagraph('【解答】');
  ap.setHeading(DocumentApp.ParagraphHeading.HEADING2);

  const cols  = 3;
  const rows  = Math.ceil(cards.length / cols);
  const aTable = body.appendTable();

  const aHdr = aTable.appendTableRow();
  for (let c = 0; c < cols; c++) {
    ['番号', '答え'].forEach(h => {
      const cell = aHdr.appendTableCell(h);
      cell.setBackgroundColor('#0D2137');
      cell.getChild(0).asText().setForegroundColor('#FFFFFF').setBold(true);
    });
  }

  for (let r = 0; r < rows; r++) {
    const row = aTable.appendTableRow();
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      if (idx < cards.length) {
        row.appendTableCell(String(idx + 1));
        row.appendTableCell(cards[idx].answer)
           .getChild(0).asText().setBold(true).setForegroundColor('#000000');
      } else {
        row.appendTableCell('');
        row.appendTableCell('');
      }
    }
  }

  doc.saveAndClose();

  // 出力フォルダへ移動
  const f = DriveApp.getFileById(doc.getId());
  outputFolder.addFile(f);
  DriveApp.getRootFolder().removeFile(f);
}

// ─── トリガー設定（初回1回だけ実行する）──────────

function setupTrigger() {
  // 既存トリガーを全削除してから再登録
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('checkAndProcess')
    .timeBased()
    .everyMinutes(5)
    .create();
  console.log('トリガー設定完了：5分ごとに自動実行します。');
}
