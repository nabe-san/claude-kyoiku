// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 授業記録 自動生成スクリプト（Google Apps Script）
// Notta .txt → 授業記録PDF（脚注付き）+ Classroom配信
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// ─── 設定（年度替わりにここだけ変更）────────────────

const SUBJECTS = {
  '歴史総合': {
    inputFolderId:  'YOUR_REKISHI_INPUT_ID',
    outputFolderId: 'YOUR_REKISHI_OUTPUT_ID',
    classroomId:    '849049892842',          // Classroom の数字ID（URLのbase64ではない）
  },
  '日本史探究': {
    inputFolderId:  'YOUR_NIHONSHI_INPUT_ID',
    outputFolderId: 'YOUR_NIHONSHI_OUTPUT_ID',
    classroomId:    'YOUR_NIHONSHI_CLASSROOM_ID', // Classroom作成後に数字IDを設定
  },
  '公共': {
    inputFolderId:  'YOUR_KOKYO_INPUT_ID',
    outputFolderId: 'YOUR_KOKYO_OUTPUT_ID',
    classroomId:    '849048536644',          // Classroom の数字ID
  },
};

// ─── メイン処理 ──────────────────────────────────

function checkAndProcess() {
  const apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    console.log('【エラー】ANTHROPIC_API_KEY が未設定です。スクリプトのプロパティに登録してください。');
    return;
  }

  for (const [subject, config] of Object.entries(SUBJECTS)) {
    const inputFolder  = DriveApp.getFolderById(config.inputFolderId);
    const outputFolder = DriveApp.getFolderById(config.outputFolderId);

    // 処理済みファイル名を収集（output内のPDF名から判定）
    const processed = new Set();
    const outFiles = outputFolder.getFiles();
    while (outFiles.hasNext()) {
      const name = outFiles.next().getName();
      processed.add(name.replace(/　授業記録\.pdf$/i, ''));
    }

    // .txt ファイルを走査
    const inFiles = inputFolder.getFiles();
    while (inFiles.hasNext()) {
      const file = inFiles.next();
      const name = file.getName();
      const mime = file.getMimeType();
      const isText = mime === 'text/plain' || name.endsWith('.txt') || mime === 'application/vnd.google-apps.document';
      if (!isText) continue;

      const baseName = name.replace(/\.txt$/i, '');
      if (processed.has(baseName)) continue;

      console.log(`[処理中] ${subject} / ${name}`);
      try {
        let transcript;
      if (mime === 'application/vnd.google-apps.document') {
        const exportUrl = 'https://www.googleapis.com/drive/v3/files/' + file.getId() + '/export?mimeType=text/plain';
        const exportRes = UrlFetchApp.fetch(exportUrl, {
          headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() }
        });
        transcript = exportRes.getContentText('UTF-8');
      } else {
        transcript = file.getBlob().getDataAsString('UTF-8');
      }
        const lesson = generateLesson(transcript, subject, apiKey);
        const docId  = createDoc(lesson, baseName, subject);
        const pdfId  = exportPdf(docId, baseName, outputFolder);
        DriveApp.getFileById(docId).setTrashed(true); // 中間Docを削除
        postToClassroom(pdfId, baseName, subject, config.classroomId);
        console.log(`[完了] ${subject} / ${baseName}`);
      } catch (e) {
        console.error(`[エラー] ${subject} / ${name}: ${e.message}`);
      }
    }
  }
}

// ─── 授業記録生成（Claude API）────────────────────

function generateLesson(transcript, subject, apiKey) {
  const system = [
    `あなたは高校${subject}の授業記録を作成するAIです。`,
    '提供された授業の文字起こし（Nottaのテキスト：誤字・句読点の誤りあり）から授業記録文書を生成します。',
    '',
    '【処理手順】',
    '1. 文字起こしの誤字・句読点・話し言葉を修正し、読みやすい文章に整形する',
    '2. 授業内容を論理的な構造（見出し＋本文）に整理する',
    '3. 授業についていけなかった生徒のために、専門用語・歴史用語に脚注を付ける',
    '4. 関連書籍を3〜5冊紹介する（岩波新書・中公新書・ちくま新書・講談社現代新書・ちくまプリマー新書・岩波ジュニア新書・平凡社新書・岩波ブックレット・NHKブックス・歴史文化ライブラリー・講談社選書メチエ・角川選書など高校生が読めるレベルのものに限定する。学術書・専門書は除く）',
    '',
    '【脚注のルール】',
    '- 高校生が「なんだっけ」となりそうな語句のみ（多すぎない、1授業で5〜10語が目安）',
    '- 解説は2〜3文、高校生がわかる平易な言葉で書く',
    '- termには本文中に実際に登場する語句をそのまま指定する',
    '',
    '【出力形式】JSONのみ（前後の説明文なし）',
    '',
    '{',
    '  "title": "授業タイトル（30字以内）",',
    '  "summary": "授業の要点を3文で（冒頭の導入として使用）",',
    '  "sections": [',
    '    {',
    '      "heading": "見出し",',
    '      "body": "本文。用語はそのまま使用（脚注付与はシステムが行う）"',
    '    }',
    '  ],',
    '  "terms": [',
    '    {',
    '      "term": "本文中に登場する語句（完全一致）",',
    '      "explanation": "高校生向けのかみ砕いた解説（2〜3文）"',
    '    }',
    '  ],',
    '  "books": [',
    '    {',
    '      "title": "書名",',
    '      "author": "著者名",',
    '      "description": "この本で何が学べるか（40字以内）"',
    '    }',
    '  ]',
    '}'
  ].join('\n');

  const payload = {
    model: 'claude-sonnet-4-6',
    max_tokens: 8000,
    system: system,
    messages: [{
      role: 'user',
      content: `以下の${subject}の授業文字起こしから授業記録を生成してください。\n\n${transcript.slice(0, 20000)}`
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
  const match = text.match(/\{[\s\S]*\}/);
  if (!match) throw new Error('JSONが見つかりませんでした: ' + text.slice(0, 200));
  return JSON.parse(match[0]);
}

// ─── Google Doc 作成 ──────────────────────────────

function createDoc(lesson, baseName, subject) {
  const docTitle = `${baseName}　授業記録`;
  const doc  = DocumentApp.create(docTitle);
  const body = doc.getBody();

  // タイトル
  const titlePara = body.appendParagraph(lesson.title);
  titlePara.setHeading(DocumentApp.ParagraphHeading.HEADING1);
  titlePara.setAlignment(DocumentApp.HorizontalAlignment.CENTER);

  // 科目・ファイル名
  body.appendParagraph(`${subject}　${baseName}`).setFontSize(10);
  body.appendParagraph('');

  // 要点（冒頭まとめ）
  const summaryPara = body.appendParagraph(`【授業の要点】\n${lesson.summary}`);
  summaryPara.setFontSize(10);
  body.appendParagraph('');

  // 本文セクション
  lesson.sections.forEach(section => {
    const h = body.appendParagraph(section.heading);
    h.setHeading(DocumentApp.ParagraphHeading.HEADING2);
    body.appendParagraph(section.body).setFontSize(11);
    body.appendParagraph('');
  });

  // 関連書籍
  const booksHeading = body.appendParagraph('関連書籍');
  booksHeading.setHeading(DocumentApp.ParagraphHeading.HEADING2);
  lesson.books.forEach((book, i) => {
    const searchUrl = 'https://www.amazon.co.jp/s?k=' + encodeURIComponent(book.title + ' ' + book.author);
    body.appendParagraph(`${i + 1}. 『${book.title}』${book.author}`).setFontSize(11);
    body.appendParagraph(`   ${book.description}`).setFontSize(10);
    body.appendParagraph(`   Amazon検索: ${searchUrl}`).setFontSize(9);
    body.appendParagraph('');
  });

  doc.saveAndClose();

  // 脚注を Docs REST API で追加（end から順に処理）
  addFootnotes(doc.getId(), lesson.terms);

  return doc.getId();
}

// ─── 脚注追加（Docs REST API）────────────────────

function addFootnotes(docId, terms) {
  if (!terms || terms.length === 0) return;

  const token   = ScriptApp.getOAuthToken();
  const baseUrl = 'https://docs.googleapis.com/v1/documents/' + docId;

  // ドキュメント構造を取得して各タームの出現インデックスを特定
  const docRes  = UrlFetchApp.fetch(baseUrl, {
    headers: { Authorization: 'Bearer ' + token }
  });
  const docJson = JSON.parse(docRes.getContentText());

  const termPositions = [];
  for (const termObj of terms) {
    const idx = findTermIndex(docJson, termObj.term);
    if (idx !== -1) {
      termPositions.push({
        term:        termObj.term,
        explanation: termObj.explanation,
        index:       idx
      });
    }
  }

  // インデックスが大きい順（文末側）から処理して前方インデックスのズレを防ぐ
  termPositions.sort((a, b) => b.index - a.index);

  for (const tp of termPositions) {
    // 脚注参照マークをタームの直後に挿入
    const createRes = UrlFetchApp.fetch(baseUrl + ':batchUpdate', {
      method:  'post',
      headers: {
        Authorization:  'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify({
        requests: [{
          createFootnote: {
            location: { index: tp.index + tp.term.length }
          }
        }]
      }),
      muteHttpExceptions: true
    });

    const createJson = JSON.parse(createRes.getContentText());
    if (createJson.error) {
      console.error('脚注挿入エラー [' + tp.term + ']: ' + createJson.error.message);
      continue;
    }

    const footnoteId = createJson.replies[0].createFootnote.footnoteId;

    // 脚注本文を挿入
    UrlFetchApp.fetch(baseUrl + ':batchUpdate', {
      method:  'post',
      headers: {
        Authorization:  'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify({
        requests: [{
          insertText: {
            location: { segmentId: footnoteId, index: 0 },
            text: tp.explanation
          }
        }]
      }),
      muteHttpExceptions: true
    });
  }
}

// ─── テキスト内のターム位置を検索（最初の出現のみ）──

function findTermIndex(docJson, term) {
  const content = docJson.body.content;
  for (const element of content) {
    if (!element.paragraph) continue;
    for (const pe of element.paragraph.elements) {
      if (!pe.textRun) continue;
      const text = pe.textRun.content;
      const pos  = text.indexOf(term);
      if (pos !== -1) {
        return pe.startIndex + pos;
      }
    }
  }
  return -1;
}

// ─── PDF 出力 ────────────────────────────────────

function exportPdf(docId, baseName, outputFolder) {
  const docFile = DriveApp.getFileById(docId);
  const pdf     = docFile.getAs('application/pdf');
  pdf.setName(baseName + '　授業記録.pdf');
  const savedPdf = outputFolder.createFile(pdf);
  return savedPdf.getId();
}

// ─── Google Classroom 配信 ───────────────────────

function postToClassroom(fileId, baseName, subject, classroomId) {
  if (!classroomId || classroomId.indexOf('YOUR_') === 0) {
    console.log('[Classroom] ' + subject + ' のIDが未設定のためスキップ');
    return;
  }

  const token = ScriptApp.getOAuthToken();

  // ファイルを「リンクを知っている全員が閲覧可能」に設定
  DriveApp.getFileById(fileId).setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  const material = {
    title:       baseName + '　授業記録',
    description: subject + 'の授業記録PDFです。',
    materials:   [{ driveFile: { driveFile: { id: fileId }, shareMode: 'VIEW' } }],
    state:       'PUBLISHED'
  };

  const res = UrlFetchApp.fetch(
    'https://classroom.googleapis.com/v1/courses/' + classroomId + '/courseWorkMaterials',
    {
      method:  'post',
      headers: {
        Authorization:  'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      payload:            JSON.stringify(material),
      muteHttpExceptions: true
    }
  );

  const json = JSON.parse(res.getContentText());
  if (json.error) {
    console.error('[Classroom エラー] ' + json.error.message);
  } else {
    console.log('[Classroom] 配信完了: ' + subject + ' / ' + baseName);
  }
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
