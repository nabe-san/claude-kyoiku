// ==========================================
// Vault 読書ノート生成 GAS（手動実行版）
// ==========================================
//
// セットアップ:
//   1. GAS エディタ > プロジェクトの設定 > スクリプトプロパティ に設定:
//      GEMINI_API_KEY        : Google AI Studio の API キー（AIzaSy... で始まる）
//      BOOKS_VAULT_FOLDER_ID : Drive の books-vault フォルダ ID
//   2. GAS エディタ > サービス > Drive API を追加する（OCR に使用）
//
// Drive フォルダ構成:
//   books-vault/               ← BOOKS_VAULT_FOLDER_ID が指すフォルダ
//     [slug]/                  ← 本ごとのフォルダ（手動で作成）
//       meta.json              ← 書誌情報（手動で作成）
//       page_001.jpg           ← 書き込み済みページ画像（手動で配置）
//       page_002.jpg
//       processing.json        ← GAS が自動生成・更新
//       [slug].md              ← 最終出力（全ページ完了後に生成）
//
// meta.json の形式:
//   {
//     "title": "明日のための近代史",
//     "author": "伊勢弘志",
//     "year": 2022,
//     "concepts_hint": ["帝国主義", "国民国家", "近代化", "万国公法"]
//   }
//
// 実行方法:
//   1. 下の SLUG を処理する本の slug に変更する
//   2. processBook() を選択して「実行」ボタンを押す
//   3. 未処理ページが残っていれば再度実行する
// ==========================================

const SLUG = 'ashita-no-kindaishi'; // ← 処理する本の slug に変更する
const BATCH_SIZE = 5;                // ← 1回で処理するページ数

// ==========================================
// メイン実行関数
// ==========================================

function processBook() {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  const vaultFolderId = props.getProperty('BOOKS_VAULT_FOLDER_ID');

  if (!apiKey) throw new Error('スクリプトプロパティに GEMINI_API_KEY を設定してください');
  if (!vaultFolderId) throw new Error('スクリプトプロパティに BOOKS_VAULT_FOLDER_ID を設定してください');

  const vaultFolder = DriveApp.getFolderById(vaultFolderId);
  const bookFolder = getSubFolder(vaultFolder, SLUG);
  if (!bookFolder) throw new Error(`Drive に "${SLUG}" フォルダが見つかりません`);

  const meta = loadMeta(bookFolder);
  Logger.log(`書誌情報: 『${meta.title}』 ${meta.author}`);

  let data = loadOrInitProcessingJson(bookFolder, meta);
  const imageFiles = getPageFiles(bookFolder);
  data = syncPages(data, imageFiles);

  const total = data.pages.length;
  const pending = data.pages.filter(p => p.status === 'pending').length;
  Logger.log(`全 ${total} ページ / 未処理 ${pending} ページ`);

  let processed = 0;

  for (let i = 0; i < data.pages.length; i++) {
    if (processed >= BATCH_SIZE) break;
    const page = data.pages[i];
    if (page.status !== 'pending') continue;

    Logger.log(`処理中: ${page.page} ページ目`);

    try {
      // 当該ページの OCR（キャッシュ済みでなければ実行）
      if (!page.ocr_text) {
        Logger.log('  OCR 実行中...');
        page.ocr_text = runOcr(page.image_file_id);
      }

      // 前後ページの OCR（前後コンテキスト用。こちらもキャッシュ優先）
      if (i > 0 && !data.pages[i - 1].ocr_text) {
        data.pages[i - 1].ocr_text = runOcr(data.pages[i - 1].image_file_id);
      }
      if (i < data.pages.length - 1 && !data.pages[i + 1].ocr_text) {
        data.pages[i + 1].ocr_text = runOcr(data.pages[i + 1].image_file_id);
      }

      const prevOcr = i > 0 ? (data.pages[i - 1].ocr_text || '') : '';
      const nextOcr = i < data.pages.length - 1 ? (data.pages[i + 1].ocr_text || '') : '';

      // Gemini Vision API 呼び出し
      Logger.log('  Gemini Vision API 送信中...');
      page.vault_fragment = callGemini(apiKey, page.image_file_id, page.ocr_text, prevOcr, nextOcr, meta);
      page.status = 'done';

    } catch (e) {
      Logger.log(`  エラー: ${e.message}`);
      page.vault_fragment = null;
      page.status = 'error';
    }

    page.processed_at = new Date().toISOString();
    processed++;

    // 1ページごとに保存（タイムアウト時も進捗を保持するため）
    saveProcessingJson(bookFolder, data);
  }

  Logger.log(`${processed} ページを処理しました`);

  // 全ページ完了したら Vault Markdown を生成
  const allDone = data.pages.every(p => p.status === 'done' || p.status === 'error');
  if (allDone) {
    data.status = 'complete';
    saveProcessingJson(bookFolder, data);
    const markdown = buildVaultMarkdown(data);
    saveOutput(bookFolder, markdown);
    Logger.log(`完了: ${SLUG}.md を生成しました`);
    Logger.log('  ⚠ 引用は必ず原本と照合してください');
    Logger.log('  ⚠ 公開する引用には <!-- featured --> を手動で追加してください');
  } else {
    const remaining = data.pages.filter(p => p.status === 'pending').length;
    Logger.log(`残り ${remaining} ページ。再度 processBook() を実行してください`);
  }
}

// ==========================================
// 書誌情報
// ==========================================

function loadMeta(bookFolder) {
  const content = getFileContent(bookFolder, 'meta.json');
  if (!content) throw new Error(`"${bookFolder.getName()}" フォルダに meta.json が見つかりません`);
  return JSON.parse(content);
}

// ==========================================
// 画像ファイル取得
// ==========================================

function getPageFiles(folder) {
  const supported = new Set(['image/jpeg', 'image/png', 'image/webp']);
  const files = [];
  const iter = folder.getFiles();
  while (iter.hasNext()) {
    const f = iter.next();
    if (supported.has(f.getMimeType())) {
      files.push({ name: f.getName(), id: f.getId() });
    }
  }
  // ファイル名順にソートして処理順を固定する
  files.sort((a, b) => a.name.localeCompare(b.name, 'ja'));
  return files;
}

// ==========================================
// processing.json の管理
// ==========================================

function loadOrInitProcessingJson(bookFolder, meta) {
  const content = getFileContent(bookFolder, 'processing.json');
  if (content) {
    Logger.log('既存の processing.json を読み込みました');
    return JSON.parse(content);
  }
  Logger.log('processing.json を新規作成します');
  return {
    slug: SLUG,
    title: meta.title,
    author: meta.author,
    year: meta.year || null,
    status: 'in_progress',
    pages: []
  };
}

function syncPages(data, imageFiles) {
  // 既存ページデータを image_file_id でインデックス化
  const existing = {};
  for (const page of data.pages) {
    existing[page.image_file_id] = page;
  }

  // 画像ファイルリストをもとにページリストを再構築
  // フォルダに新しい画像が追加されても自動的に取り込まれる
  data.pages = imageFiles.map((file, index) => {
    if (existing[file.id]) return existing[file.id];
    return {
      page: index + 1,
      image_file_id: file.id,
      ocr_text: null,        // OCR キャッシュ（処理時に自動入力）
      status: 'pending',
      processed_at: null,
      vault_fragment: null   // null=未処理 / ""=書き込みなし / "文字列"=引用あり
    };
  });

  return data;
}

function saveProcessingJson(bookFolder, data) {
  upsertFile(bookFolder, 'processing.json', JSON.stringify(data, null, 2));
}

// ==========================================
// OCR（Drive API v2 を使用）
// ==========================================

function runOcr(fileId) {
  const file = DriveApp.getFileById(fileId);
  const blob = file.getBlob();

  // 画像を Google ドキュメントに変換（OCR）
  const inserted = Drive.Files.insert(
    { title: '_ocr_temp_', mimeType: 'application/vnd.google-apps.document' },
    blob,
    { ocr: true, ocrLanguage: 'ja' }
  );

  // テキストを取得して一時ファイルを削除
  const doc = DocumentApp.openById(inserted.id);
  const text = doc.getBody().getText();
  DriveApp.getFileById(inserted.id).setTrashed(true);

  return text;
}

// ==========================================
// Gemini Vision API
// ==========================================

function buildPrompt(meta, currOcr, prevOcr, nextOcr) {
  const conceptsHint = (meta.concepts_hint || []).join('・') || '（未設定）';
  const citation = `*${meta.author}『${meta.title}』（${meta.year || ''}年）*`;

  return `これは書籍のページ画像です。読者が書き込んだ記号に従って引用箇所を特定し、抽出してください。

【書誌情報】
タイトル：${meta.title}
著者：${meta.author}
出版年：${meta.year || ''}年

【書き込み記号の意味】
◎　　… 極めて重要。その行・段落を引用する
縦線 … 余白に引いた縦の線。隣接するテキストブロック全体が重要
横線 … 文字の下に引いた線。その行またはその段落が重要

印刷の罫線や装飾と区別すること。読者の手書き記号のみを対象にしてください。

【OCR 参照テキスト（引用の正確な文字起こしに活用すること）】
--- 前ページ ---
${prevOcr || '（なし）'}
--- 当該ページ ---
${currOcr || '（なし）'}
--- 次ページ ---
${nextOcr || '（なし）'}

※ どの箇所を引用するかは必ず画像の書き込み記号から判断してください。
   OCR テキストは文字列の正確性確認にのみ使ってください。

【引用ルール】
- 記号のある箇所を起点に、文として意味が完結する範囲を抽出する
- 引用は原文のまま。一字一句変えない。要約・言い換えは禁止
- 複数行にわたる場合は各行の先頭に「> 」を付ける
- 書き込み記号の開始点がこのページ画像内にある箇所のみを対象とする（重複防止）

【概念タグ候補】
${conceptsHint}
リストにない概念が必要な場合は末尾に「新規タグ候補: ○○」と別記する。

【出力フォーマット】
書き込みのある箇所のみ以下の形式で出力する。書き込みがない場合は何も出力しない。

<!-- concepts: タグ1, タグ2 -->
## テーマを端的に表す見出し（15字以内）

> 引用テキスト

${citation}

---

【禁止事項（厳守）】
- <!-- featured --> は絶対に出力しない
- 引用の後に解説・要約・コメントを書かない
- 「以下に引用を提示します」などの前置き文を書かない
- 授業活用メモ・教師向けコメントを書かない`;
}

function callGemini(apiKey, fileId, currOcr, prevOcr, nextOcr, meta) {
  const file = DriveApp.getFileById(fileId);
  const blob = file.getBlob();
  const base64 = Utilities.base64Encode(blob.getBytes());

  const payload = {
    contents: [{
      parts: [
        { text: buildPrompt(meta, currOcr, prevOcr, nextOcr) },
        { inlineData: { mimeType: blob.getContentType(), data: base64 } }
      ]
    }],
    generationConfig: { temperature: 0.1 }
  };

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const result = JSON.parse(res.getContentText());
  if (result.error) throw new Error(`Gemini API エラー: ${result.error.message}`);

  return (result.candidates?.[0]?.content?.parts?.[0]?.text || '').trim();
}

// ==========================================
// Vault Markdown 生成
// ==========================================

function buildVaultMarkdown(data) {
  const frontmatter = [
    '---',
    `ref: ${data.slug}`,
    `title: ${data.title}`,
    `author: ${data.author}`,
    `year: ${data.year || ''}`,
    '---',
    ''
  ].join('\n');

  const body = data.pages
    .filter(p => p.vault_fragment && p.vault_fragment.trim() !== '')
    .map(p => p.vault_fragment.trim())
    .join('\n\n');

  return frontmatter + body + '\n';
}

function saveOutput(bookFolder, markdown) {
  upsertFile(bookFolder, `${SLUG}.md`, markdown);
}

// ==========================================
// ユーティリティ
// ==========================================

function getSubFolder(parentFolder, name) {
  const iter = parentFolder.getFoldersByName(name);
  return iter.hasNext() ? iter.next() : null;
}

function getFileContent(folder, filename) {
  const iter = folder.getFilesByName(filename);
  return iter.hasNext() ? iter.next().getBlob().getDataAsString('UTF-8') : null;
}

function upsertFile(folder, filename, content) {
  const iter = folder.getFilesByName(filename);
  const blob = Utilities.newBlob(content, MimeType.PLAIN_TEXT, filename);
  if (iter.hasNext()) {
    // Drive API v2 で内容を上書き更新
    Drive.Files.update({}, iter.next().getId(), blob);
  } else {
    folder.createFile(blob);
  }
}
