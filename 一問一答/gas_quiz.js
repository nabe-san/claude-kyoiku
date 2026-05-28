// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 授業文字起こし（.txt） → 4択確認テスト 自動生成スクリプト
// Notta等でエクスポートした .txt をinputに置くと自動生成
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const INPUT_FOLDER_ID  = '1B2QEP9FAvzYyFv68ixbtaqg6Y0NJIFeY';
const OUTPUT_FOLDER_ID = '1PTgc9d0tB5CGlniZ_WiMbjsyMe1kXkWr';

const MARKS = ['①', '②', '③', '④'];

// ─── メイン処理 ──────────────────────────────────

function checkAndProcess() {
  const apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    console.log('【エラー】ANTHROPIC_API_KEY が未設定です。スクリプトのプロパティに登録してください。');
    return;
  }

  const inputFolder  = DriveApp.getFolderById(INPUT_FOLDER_ID);
  const outputFolder = DriveApp.getFolderById(OUTPUT_FOLDER_ID);

  // 処理済みファイル名を収集
  const processed = new Set();
  const outFiles = outputFolder.getFiles();
  while (outFiles.hasNext()) {
    processed.add(outFiles.next().getName());
  }

  // テキストファイルを走査
  const inFiles = inputFolder.getFiles();
  while (inFiles.hasNext()) {
    const file = inFiles.next();
    const name = file.getName();
    const mime = file.getMimeType();

    const isText = mime === 'text/plain' || name.endsWith('.txt');
    if (!isText) continue;

    const baseName = name.replace(/\.txt$/i, '');
    const docName  = `${baseName}　確認テスト`;
    if (processed.has(docName)) continue;

    console.log(`[処理中] ${name}`);
    try {
      const transcript = file.getBlob().getDataAsString('UTF-8');
      const quiz = generateQuiz(transcript, baseName, apiKey);
      createDoc(quiz, docName, baseName, outputFolder);
      console.log(`[完了] ${docName}（${quiz.length}問）`);
    } catch (e) {
      console.error(`[エラー] ${name}: ${e.message}`);
    }
  }
}

// ─── 4択問題生成（Anthropic API）────────────────

function generateQuiz(transcript, unitName, apiKey) {
  const payload = {
    model: 'claude-sonnet-4-6',
    max_tokens: 4096,
    system: [
      'あなたは高校日本史・公共の確認テストを作成するAIです。',
      '提供された授業の文字起こしテキストから4択問題を生成します。',
      '',
      '【ルール】',
      '- 授業で説明された重要な概念・事実・因果関係から出題する',
      '- 各問題に選択肢を4つ（正答1つ・誤答3つ）作る',
      '- 誤答は紛らわしいが明確に間違いのある選択肢にする',
      '- 15〜20問作成する（少なすぎても多すぎても不可）',
      '- JSONのみ出力（前後の説明文は不要）',
      '',
      '【出力形式】',
      '[',
      '  {"question": "問題文", "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"], "answer": 0}',
      ']',
      '※ answer は正答の選択肢インデックス（0〜3）'
    ].join('\n'),
    messages: [{
      role: 'user',
      content: `以下の授業文字起こしから4択確認テストを15〜20問生成してください。\n\n${transcript.slice(0, 15000)}`
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
  if (!match) throw new Error('JSONが見つかりませんでした: ' + text.slice(0, 300));
  return JSON.parse(match[0]);
}

// ─── Googleドキュメント作成 ───────────────────────

function createDoc(quiz, docName, unitName, outputFolder) {
  const doc  = DocumentApp.create(docName);
  const body = doc.getBody();

  // タイトル
  const title = body.appendParagraph(`確認テスト　${unitName}`);
  title.setHeading(DocumentApp.ParagraphHeading.HEADING1);
  title.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
  body.appendParagraph(`全${quiz.length}問　　氏名：＿＿＿＿＿＿`).setFontSize(10);

  // 問題
  quiz.forEach((q, i) => {
    const qp = body.appendParagraph(`問${i + 1}．${q.question}`);
    qp.setAttributes({
      [DocumentApp.Attribute.BOLD]: true,
      [DocumentApp.Attribute.SPACING_BEFORE]: 12
    });
    q.choices.forEach((choice, j) => {
      const cp = body.appendParagraph(`　${MARKS[j]}　${choice}`);
      cp.setIndentStart(20);
      cp.setAttributes({ [DocumentApp.Attribute.BOLD]: false });
    });
  });

  // 解答ページ
  body.appendPageBreak();
  const ap = body.appendParagraph('【解答】');
  ap.setHeading(DocumentApp.ParagraphHeading.HEADING2);

  const cols = 3;
  const rows = Math.ceil(quiz.length / cols);
  const table = body.appendTable();

  const hdr = table.appendTableRow();
  for (let c = 0; c < cols; c++) {
    ['問', '答'].forEach(h => {
      const cell = hdr.appendTableCell(h);
      cell.setBackgroundColor('#0D2137');
      cell.getChild(0).asText().setForegroundColor('#FFFFFF').setBold(true);
    });
  }

  for (let r = 0; r < rows; r++) {
    const row = table.appendTableRow();
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      if (idx < quiz.length) {
        row.appendTableCell(String(idx + 1));
        const ans = row.appendTableCell(MARKS[quiz[idx].answer]);
        ans.getChild(0).asText().setBold(true).setForegroundColor('#000000');
      } else {
        row.appendTableCell('');
        row.appendTableCell('');
      }
    }
  }

  doc.saveAndClose();

  const f = DriveApp.getFileById(doc.getId());
  outputFolder.addFile(f);
  DriveApp.getRootFolder().removeFile(f);
}

// ─── トリガー設定（初回1回だけ実行）──────────────

function setupTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('checkAndProcess')
    .timeBased()
    .everyMinutes(5)
    .create();
  console.log('トリガー設定完了：5分ごとに自動実行します。');
}
