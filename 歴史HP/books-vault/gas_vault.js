// ==========================================
// Vault 読書ノート生成 GAS（手動実行版）
// ==========================================
//
// このスクリプトは既存OCRパイプライン（mojika.js）の後段処理です。
// OCR は行いません。既存パイプラインが生成した _MERGED Doc を読み取ります。
//
// 役割の分担:
//   既存GAS (mojika.js) : 画像/PDF → OCR Doc → [bookname]_MERGED Doc
//   このスクリプト      : _MERGED Doc + 元画像 → Gemini Vision → Vault Markdown
//
// セットアップ:
//   GAS エディタ > プロジェクトの設定 > スクリプトプロパティ に以下を設定:
//     GEMINI_API_KEY        : Google AI Studio の API キー（AIzaSy... で始まる）
//     BOOKS_VAULT_FOLDER_ID : Drive の books-vault フォルダ ID
//     BOOK_MERGED_FOLDER_ID : 既存パイプラインの BOOK_MERGED フォルダ ID
//                             （mojika.js の MERGE_CFG.BOOK_MERGED_FOLDER_ID と同じ値）
//     TARGET_SLUG           : （任意）処理する本の slug
//
//   Drive API（Advanced Service）は不要です。
//
// Drive フォルダ構成:
//   books-vault/               ← BOOKS_VAULT_FOLDER_ID
//     [slug]/
//       meta.json              ← 書誌情報（手動作成）
//       page_001.jpg           ← 書き込み済みページ画像（手動配置）
//       processing.json        ← GAS が自動生成・更新
//       [slug].md              ← Vault 最終出力
//
//   BOOK_MERGED/               ← BOOK_MERGED_FOLDER_ID（既存パイプライン管理）
//     [bookname]_MERGED        ← 既存GASが生成。このスクリプトは読み取るだけ
//
// meta.json の形式:
//   {
//     "title": "明日のための近代史",
//     "author": "伊勢弘志",
//     "year": 2022,
//     "merged_doc_name": "明日のための近代史_MERGED",
//     "concepts_hint": ["帝国主義", "国民国家", "近代化", "万国公法"]
//   }
//
//   merged_doc_name: BOOK_MERGED フォルダ内の Google Doc 名。
//                    未設定の場合は OCR テキストなしで続行します。
//
// 実行方法:
//   1. TARGET_SLUG を設定するか、下の SLUG 定数を書き換える
//   2. processBook() を選択して「実行」ボタンを押す
//   3. 未処理ページが残っていれば再度実行する
// ==========================================

const SLUG = PropertiesService.getScriptProperties().getProperty('TARGET_SLUG')
             || 'ashita-no-kindaishi';
const BATCH_SIZE = 5;

// ==========================================
// メイン実行関数
// ==========================================

function processBook() {
  const props = PropertiesService.getScriptProperties();
  const apiKey        = props.getProperty('GEMINI_API_KEY');
  const vaultFolderId = props.getProperty('BOOKS_VAULT_FOLDER_ID');
  const mergedFolderId = props.getProperty('BOOK_MERGED_FOLDER_ID');

  if (!apiKey)         throw new Error('スクリプトプロパティに GEMINI_API_KEY を設定してください');
  if (!vaultFolderId)  throw new Error('スクリプトプロパティに BOOKS_VAULT_FOLDER_ID を設定してください');
  if (!mergedFolderId) throw new Error('スクリプトプロパティに BOOK_MERGED_FOLDER_ID を設定してください');

  const vaultFolder = DriveApp.getFolderById(vaultFolderId);
  const bookFolder  = getSubFolder(vaultFolder, SLUG);
  if (!bookFolder) throw new Error(`Drive に "${SLUG}" フォルダが見つかりません`);

  const meta = loadMeta(bookFolder);
  Logger.log(`書誌情報: 『${meta.title}』 ${meta.author}`);

  // _MERGED Doc からページ別OCRテキストをまとめて取得（実行中に1回だけ）
  let ocrMap = new Map();
  if (meta.merged_doc_name) {
    Logger.log(`_MERGED Doc 読み込み中: ${meta.merged_doc_name}`);
    ocrMap = loadMergedOcr(mergedFolderId, meta.merged_doc_name);
    Logger.log(`  OCRテキスト取得: ${ocrMap.size} セクション`);
  } else {
    Logger.log('⚠ meta.json に merged_doc_name が未設定。OCRテキストなしで続行します');
  }

  let data = loadOrInitProcessingJson(bookFolder, meta);
  const imageFiles = getPageFiles(bookFolder);
  data = syncPages(data, imageFiles);

  const total   = data.pages.length;
  const pending = data.pages.filter(p => p.status === 'pending').length;
  Logger.log(`全 ${total} ページ / 未処理 ${pending} ページ`);

  let processed = 0;

  for (let i = 0; i < data.pages.length; i++) {
    if (processed >= BATCH_SIZE) break;
    const page = data.pages[i];
    if (page.status !== 'pending') continue;

    Logger.log(`処理中: ${page.page} ページ目（${page.image_name}）`);

    try {
      // OCRテキストをキャッシュ。未取得（null）なら ocrMap から補完する
      if (page.ocr_text === null) {
        page.ocr_text = ocrMap.get(imageBaseName(page.image_name)) || '';
      }
      const prevPage = i > 0 ? data.pages[i - 1] : null;
      const nextPage = i < data.pages.length - 1 ? data.pages[i + 1] : null;
      if (prevPage && prevPage.ocr_text === null) {
        prevPage.ocr_text = ocrMap.get(imageBaseName(prevPage.image_name)) || '';
      }
      if (nextPage && nextPage.ocr_text === null) {
        nextPage.ocr_text = ocrMap.get(imageBaseName(nextPage.image_name)) || '';
      }

      const prevOcr = prevPage ? (prevPage.ocr_text || '') : '';
      const nextOcr = nextPage ? (nextPage.ocr_text || '') : '';

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
    saveProcessingJson(bookFolder, data);
  }

  Logger.log(`${processed} ページを処理しました`);

  const allDone = data.pages.every(p => p.status === 'done' || p.status === 'error');
  if (allDone) {
    data.status = 'complete';
    saveProcessingJson(bookFolder, data);
    const markdown = buildVaultMarkdown(data);
    saveOutput(bookFolder, markdown);
    Logger.log(`完了: ${SLUG}.md を生成しました`);
    Logger.log('  ⚠ 引用は必ず原本と照合してください（Gemini の誤読の可能性あり）');
    publishToGitHub(SLUG, meta, markdown);
  } else {
    const remaining = data.pages.filter(p => p.status === 'pending').length;
    Logger.log(`残り ${remaining} ページ。再度 processBook() を実行してください`);
  }
}

// ==========================================
// エラーページをリセットして再試行可能にする
// ==========================================

function resetErrors() {
  const vaultFolderId = PropertiesService.getScriptProperties().getProperty('BOOKS_VAULT_FOLDER_ID');
  if (!vaultFolderId) throw new Error('スクリプトプロパティに BOOKS_VAULT_FOLDER_ID を設定してください');

  const vaultFolder = DriveApp.getFolderById(vaultFolderId);
  const bookFolder  = getSubFolder(vaultFolder, SLUG);
  if (!bookFolder) throw new Error(`Drive に "${SLUG}" フォルダが見つかりません`);

  const content = getFileContent(bookFolder, 'processing.json');
  if (!content) { Logger.log('processing.json が見つかりません'); return; }

  const data = JSON.parse(content);
  let count = 0;
  for (const page of data.pages) {
    if (page.status === 'error') {
      page.status         = 'pending';
      page.vault_fragment = null;
      page.processed_at   = null;
      count++;
    }
  }
  if (data.status === 'complete') data.status = 'in_progress';

  saveProcessingJson(bookFolder, data);
  Logger.log(`${count} ページを pending にリセットしました。processBook() を実行してください`);
}

// ==========================================
// 書誌情報
// ==========================================

function loadMeta(bookFolder) {
  const content = getFileContent(bookFolder, 'meta.json');
  if (!content) throw new Error(`"${bookFolder.getName()}" フォルダに meta.json が見つかりません`);
  const meta = JSON.parse(content);
  if (!meta.title)  throw new Error('meta.json に title フィールドがありません');
  if (!meta.author) throw new Error('meta.json に author フィールドがありません');
  return meta;
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
  files.sort((a, b) => a.name.localeCompare(b.name, 'ja'));
  return files;
}

// ==========================================
// _MERGED Doc からページ別OCRテキストを取得
// ==========================================

function loadMergedOcr(mergedFolderId, mergedDocName) {
  const folder = DriveApp.getFolderById(mergedFolderId);
  const iter = folder.getFilesByName(mergedDocName);
  if (!iter.hasNext()) {
    Logger.log(`⚠ "${mergedDocName}" が BOOK_MERGED フォルダに見つかりません。OCRなしで続行します`);
    return new Map();
  }
  const file = iter.next();
  if (file.getMimeType() !== MimeType.GOOGLE_DOCS) {
    Logger.log(`⚠ "${mergedDocName}" は Google Doc ではありません`);
    return new Map();
  }
  const doc = DocumentApp.openById(file.getId());
  return parseMergedDoc(doc.getBody().getText());
}

function parseMergedDoc(text) {
  // 既存パイプライン（C_mergeDocsByBook）が生成する構造を解析する:
  //   ▼ [basename]_OCR（date）  ← セクション区切り行（太字だが getText では区別不可）
  //   [そのページのOCRテキスト]
  //
  // basename は画像ファイル名から拡張子を除いたものと一致する。
  // 例: "▼ 明日のための近代史_10_OCR（2026/06/28...）" → key: "明日のための近代史_10"
  const map = new Map();
  const lines = text.split(/\r?\n/);
  let currentKey   = null;
  let currentLines = [];

  for (const line of lines) {
    if (line.startsWith('▼ ')) {
      if (currentKey) map.set(currentKey, currentLines.join('\n').trim());
      // "_OCR（" または "_OCR(" の直前までを basename として取り出す
      const key = line.replace(/^▼\s+/, '').replace(/_OCR[（(].*$/, '').trim();
      currentKey   = key || null;
      currentLines = [];
    } else if (currentKey) {
      currentLines.push(line);
    }
  }
  if (currentKey) map.set(currentKey, currentLines.join('\n').trim());

  return map;
}

function imageBaseName(filename) {
  return filename ? filename.replace(/\.[^.]+$/, '') : '';
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
    slug:   SLUG,
    title:  meta.title,
    author: meta.author,
    year:   meta.year || null,
    status: 'in_progress',
    pages:  []
  };
}

function syncPages(data, imageFiles) {
  const existing = {};
  for (const page of data.pages) existing[page.image_file_id] = page;

  data.pages = imageFiles.map((file, index) => {
    const existingPage = existing[file.id];
    if (existingPage) {
      if (!existingPage.image_name) existingPage.image_name = file.name; // 旧形式との互換
      return existingPage;
    }
    return {
      page:           index + 1,
      image_name:     file.name,
      image_file_id:  file.id,
      ocr_text:       null,   // null=未取得 / ""=取得済みだがOCRなし / "文字列"=OCRあり
      status:         'pending',
      processed_at:   null,
      vault_fragment: null    // null=未処理 / ""=書き込みなし / "文字列"=引用あり
    };
  });

  return data;
}

function saveProcessingJson(bookFolder, data) {
  upsertFile(bookFolder, 'processing.json', JSON.stringify(data, null, 2));
}

// ==========================================
// Gemini Vision API
// ==========================================

function buildPrompt(meta, currOcr, prevOcr, nextOcr) {
  const conceptsHint = (meta.concepts_hint || []).join('・') || '（未設定）';
  const citation     = `*${meta.author}『${meta.title}』（${meta.year || ''}年）*`;

  return `これは書籍のページ画像です。

【あなたの役割】
教師が読書中に付けた手書き記号（◎・縦線・横線）は、教師の思考の痕跡です。
あなたの仕事は、その記号がどこにあるかを画像から読み取り、該当箇所の文章を正確に引用することです。
「ここは重要そうだ」というAI自身の判断で引用対象を追加することは絶対に禁止します。
記号のない箇所は、どれだけ重要に見えても引用しないでください。

【書誌情報】
タイトル：${meta.title}
著者：${meta.author}
出版年：${meta.year || ''}年

【書き込み記号の読み方】
◎　　… 教師が「最重要」と判断してつけた印。その行または段落全体を引用する
縦線 … 教師が余白に引いた縦の線。その線に隣接するテキストブロック全体を引用する
横線 … 教師が文字の下に引いた線。その行またはその段落を引用する

手書き記号の見分け方：
- 手書き → ペン・鉛筆のかすれ・にじみ・手ぶれが見られる
- 印刷   → 均一できれいな線（対象外）

【OCR 参照テキスト（文字列の正確な起こしに活用すること）】
--- 前ページ ---
${prevOcr || '（なし）'}
--- 当該ページ ---
${currOcr || '（なし）'}
--- 次ページ ---
${nextOcr || '（なし）'}

OCR テキストの使い方：
- 記号箇所の特定には使わない（必ず画像を見て判断する）
- 引用した文章の文字が画像から読みにくい場合に、正確な表記を確認するためだけに使う

【引用ルール】
- 記号の開始点がこのページ画像内にある箇所のみを対象とする（前後ページへの重複防止）
- 記号のある箇所を起点に、文として意味が完結する範囲を抽出する
- 引用は原文のまま。一字一句変えない。要約・言い換えは禁止
- 複数行にわたる場合は各行の先頭に「> 」を付ける
- 1引用ブロックあたり400字を目安とする。ただし必ず文末（句点）まで引用を完結させること。文末が400字を超える場合は700字まで許容する
- 縦線が複数文にわたる場合は、その中で最も論点が明確な文を中心に引用する

【概念タグ候補】
${conceptsHint}
リストにない概念が必要な場合は引用ブロックの外に「新規タグ候補: ○○」と別記する。

【出力フォーマット】
書き込み記号のある箇所のみ以下の形式で出力する。書き込みが一切ない場合は何も出力しない。

<!-- concepts: タグ1, タグ2 -->
## テーマを端的に表す見出し（15字以内）

> 引用テキスト

${citation}

---

【禁止事項（厳守）】
- 書き込み記号のない箇所を引用しない（AIが重要だと思っても対象外）
- <!-- featured --> は絶対に出力しない
- 引用の後に解説・要約・コメントを書かない
- 「以下に引用を提示します」などの前置き文を書かない
- 授業活用メモ・教師向けコメントを書かない`;
}

function callGemini(apiKey, fileId, currOcr, prevOcr, nextOcr, meta) {
  const file   = DriveApp.getFileById(fileId);
  const blob   = file.getBlob();
  const base64 = Utilities.base64Encode(blob.getBytes());

  const payload = {
    contents: [{
      parts: [
        { text: buildPrompt(meta, currOcr, prevOcr, nextOcr) },
        { inlineData: { mimeType: blob.getContentType(), data: base64 } }
      ]
    }],
    generationConfig: { temperature: 0.5, maxOutputTokens: 8192 }
  };

  const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + apiKey;
  const res = UrlFetchApp.fetch(url, {
    method:          'post',
    contentType:     'application/json',
    payload:         JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const result = JSON.parse(res.getContentText());
  if (result.error) throw new Error('Gemini API エラー: ' + result.error.message);

  return (result.candidates?.[0]?.content?.parts?.[0]?.text || '').trim();
}

// ==========================================
// Vault Markdown 生成
// ==========================================

function buildVaultMarkdown(data) {
  const frontmatter = [
    '---',
    'ref: '    + (data.slug   || ''),
    'title: '  + (data.title  || ''),
    'author: ' + (data.author || ''),
    'year: '   + (data.year   != null ? data.year : ''),
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
  upsertFile(bookFolder, SLUG + '.md', markdown);
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
  // Drive API Advanced Service 不要。既存ファイルを削除して新規作成する。
  const blob = Utilities.newBlob(content, MimeType.PLAIN_TEXT, filename);
  const iter = folder.getFilesByName(filename);
  while (iter.hasNext()) iter.next().setTrashed(true);
  folder.createFile(blob);
}

// ==========================================
// GitHub 自動 publish
// ==========================================

/**
 * Vault MD から公開用 MD を生成し、GitHub に commit する。
 * processBook() 完了時に自動呼び出しされる。
 * GITHUB_TOKEN が未設定の場合はスキップする（後方互換）。
 */
function publishToGitHub(slug, meta, vaultMarkdown) {
  const props  = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  const token  = props.getProperty('GITHUB_TOKEN');
  const owner  = props.getProperty('GITHUB_OWNER') || 'nabe-san';
  const repo   = props.getProperty('GITHUB_REPO')  || 'claude-kyoiku';

  if (!token) {
    Logger.log('⚠ GITHUB_TOKEN 未設定 — GitHub への自動 push をスキップします');
    Logger.log('  設定後は manualPublish() を実行してください');
    return;
  }

  Logger.log('── GitHub 自動 publish 開始 ──');

  try {
    // 1. 概念タグを抽出
    const concepts = extractConceptsFromVault(vaultMarkdown);
    Logger.log(`概念タグ: ${concepts.join(', ')}`);

    // 2. 既存公開ファイルの relatedUnits を取得（上書きを防ぐ）
    const filePath = `歴史HP/src/content/books/${slug}.md`;
    const existing = getGitHubFile(token, owner, repo, filePath);
    const relatedUnits = existing ? extractRelatedUnits(existing.content) : [];
    if (relatedUnits.length > 0) {
      Logger.log(`relatedUnits を引き継ぎます: ${relatedUnits.join(', ')}`);
    }

    // 3. Gemini に引用選択を依頼
    Logger.log(`Vault 文字数: ${vaultMarkdown.length}`);
    if (vaultMarkdown.length < 500) {
      Logger.log(`⚠ Vault が短すぎます。内容: ${vaultMarkdown.substring(0, 300)}`);
    }
    Logger.log('Gemini に引用選択を依頼中...');
    const publicMd = callGeminiForSelection(apiKey, vaultMarkdown, meta, concepts, relatedUnits);
    Logger.log(`Gemini 応答文字数: ${publicMd.length}`);
    if (publicMd.length < 500) Logger.log(`Gemini 応答内容: ${publicMd}`);

    // 4. バリデーション
    validatePublicMd(publicMd, slug);

    // 5. GitHub に commit
    commitToGitHub(token, owner, repo, filePath, publicMd, slug, existing ? existing.sha : null);

    Logger.log(`✅ GitHub push 完了: ${filePath}`);
    Logger.log('  Vercel が自動デプロイします（数分後にサイトに反映）');

  } catch (e) {
    Logger.log(`❌ publish エラー: ${e.message}`);
    notifyAdminOnFailure(slug, e.message);
  }
}

/**
 * Vault が生成済みの状態から手動で publish をやり直す。
 * processBook() を実行せず、既存の Vault MD から再 publish できる。
 */
function manualPublish() {
  const props = PropertiesService.getScriptProperties();
  const vaultFolderId = props.getProperty('BOOKS_VAULT_FOLDER_ID');
  if (!vaultFolderId) throw new Error('BOOKS_VAULT_FOLDER_ID を設定してください');

  const vaultFolder   = DriveApp.getFolderById(vaultFolderId);
  const bookFolder    = getSubFolder(vaultFolder, SLUG);
  if (!bookFolder)    throw new Error(`Drive に "${SLUG}" フォルダが見つかりません`);

  const meta = loadMeta(bookFolder);
  const vaultMarkdown = getFileContent(bookFolder, SLUG + '.md');
  if (!vaultMarkdown) {
    throw new Error(`${SLUG}.md が Drive に見つかりません。先に processBook() を実行してください`);
  }

  publishToGitHub(SLUG, meta, vaultMarkdown);
}

// ==========================================
// 引用選択（Gemini テキスト API）
// ==========================================

function extractConceptsFromVault(vaultContent) {
  const seen   = new Set();
  const result = [];
  const regex  = /<!-- concepts:\s*([^-\n]+?)\s*-->/g;
  let match;
  while ((match = regex.exec(vaultContent)) !== null) {
    for (const tag of match[1].split(',')) {
      const t = tag.trim();
      if (t && !t.startsWith('新規タグ候補') && !seen.has(t)) {
        seen.add(t);
        result.push(t);
      }
    }
  }
  return result.slice(0, 8);
}

function extractRelatedUnits(content) {
  const match = content.match(/relatedUnits:\s*\n((?:[ \t]+-[^\n]+\n)*)/);
  if (!match) return [];
  return (match[1].match(/-\s+(\S+)/g) || []).map(s => s.replace(/^-\s+/, '').trim());
}

function buildPublishPrompt(vaultContent, meta, concepts, relatedUnits) {
  const conceptsStr      = concepts.slice(0, 5).join(', ') || '（未設定）';
  const conceptsYaml     = concepts.length     > 0 ? concepts.map(c     => `  - ${c}`).join('\n') : '  []';
  const relatedUnitsYaml = relatedUnits.length > 0 ? relatedUnits.map(u => `  - ${u}`).join('\n') : '  []';

  return `あなたは教師の読書ノートの編集者です。
以下は Vault（全引用ストック）です。この中から公開サイトに掲載する引用を選んでください。

【Vault（全引用）】
${vaultContent}

【選択基準（重要な順）】
1. 概念理解に役立つ——知識ではなく思考の材料になる引用
2. 授業との接続性が高い——授業テーマ「${conceptsStr}」に関連する
3. 著者の視点・論点がよく表れている——著者の独自の主張が読み取れる
4. 引用だけで考える余白がある——解説なしで読者が自分で考えられる

【除外すべきブロック】
- 同じ文が繰り返されている（反復ループ）
- 途中で文が切れている（末尾が「…」「求めたの」「五年」など中途半端）
- 1行だけの極端に短い引用（30字未満）

【選択数】
6〜10 ブロックを選ぶ。重複・欠陥があれば躊躇なく除外してよい。

【出力フォーマット】
フロントマターから始め、選んだ引用ブロックをそのまま並べる。
<!-- concepts: ... --> タグは本文から除去する。
## 見出し、> 引用、*出典* の形式はそのまま維持する。
引用ブロックの間には --- を入れる。

---
title: ${meta.title}
author: ${meta.author}
year: ${meta.year || ''}
summary: （この本の主題を2〜3文で。著者の独自の論点を中心に書く）
concepts:
${conceptsYaml}
relatedUnits:
${relatedUnitsYaml}
---

（引用ブロックをここに並べる）

【厳守事項】
- AI による解説・要約・コメントを本文に追加しない
- <!-- featured --> を出力しない
- 引用テキストは一字一句変えない
- 前置き文（「以下に引用を示します」等）を書かない`;
}

function callGeminiForSelection(apiKey, vaultContent, meta, concepts, relatedUnits) {
  const prompt  = buildPublishPrompt(vaultContent, meta, concepts, relatedUnits);
  const payload = {
    contents:         [{ parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.3, maxOutputTokens: 4096 }
  };

  const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + apiKey;
  const res = UrlFetchApp.fetch(url, {
    method:             'post',
    contentType:        'application/json',
    payload:            JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const result = JSON.parse(res.getContentText());
  if (result.error) throw new Error('Gemini API エラー: ' + result.error.message);

  let text = (result.candidates?.[0]?.content?.parts?.[0]?.text || '').trim();
  text = text.replace(/^```(?:yaml|markdown)?\s*\n/, '');
  text = text.replace(/\n```\s*$/, '');
  return text.trim();
}

// ==========================================
// バリデーション
// ==========================================

function validatePublicMd(content, slug) {
  if (!content.startsWith('---')) {
    throw new Error('フロントマターがありません（--- で始まっていない）');
  }

  const required = { title: /^title:\s*(.+)/m, author: /^author:\s*(.+)/m, year: /^year:\s*(.+)/m };
  for (const [field, re] of Object.entries(required)) {
    const m = content.match(re);
    if (!m || !m[1].trim()) {
      throw new Error(`フロントマターの ${field} がないか空です`);
    }
  }

  if (content.length < 200) {
    throw new Error(`出力が短すぎます（${content.length} 文字）。生成失敗の可能性があります`);
  }

  Logger.log(`✓ バリデーション OK（${content.length} 文字）`);
}

// ==========================================
// GitHub API
// ==========================================

function encodeGitHubPath(path) {
  return path.split('/').map(s => encodeURIComponent(s)).join('/');
}

/**
 * GitHub からファイルの内容と SHA を取得する。
 * ファイルが存在しない場合は null を返す。
 */
function getGitHubFile(token, owner, repo, path) {
  const url = `https://api.github.com/repos/${owner}/${repo}/contents/${encodeGitHubPath(path)}`;
  const res = UrlFetchApp.fetch(url, {
    method:             'get',
    headers: {
      'Authorization':        `Bearer ${token}`,
      'Accept':               'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28'
    },
    muteHttpExceptions: true
  });

  if (res.getResponseCode() === 404) return null;

  const data = JSON.parse(res.getContentText());
  if (data.message) throw new Error(`GitHub API エラー: ${data.message}`);

  const decoded = Utilities.newBlob(
    Utilities.base64Decode(data.content.replace(/\n/g, ''))
  ).getDataAsString('UTF-8');

  return { sha: data.sha, content: decoded };
}

/**
 * GitHub にファイルを作成または更新する（sha が null なら新規作成）。
 */
function commitToGitHub(token, owner, repo, path, content, slug, sha) {
  const url = `https://api.github.com/repos/${owner}/${repo}/contents/${encodeGitHubPath(path)}`;
  const now = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm');

  const body = {
    message: `books: ${slug} を Vault から自動生成 (${now})`,
    content: Utilities.base64Encode(Utilities.newBlob(content, 'UTF-8').getBytes()),
    branch:  'main'
  };
  if (sha) body.sha = sha;

  const res = UrlFetchApp.fetch(url, {
    method:             'put',
    contentType:        'application/json',
    headers: {
      'Authorization':        `Bearer ${token}`,
      'Accept':               'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28'
    },
    payload:            JSON.stringify(body),
    muteHttpExceptions: true
  });

  const code = res.getResponseCode();
  if (code !== 200 && code !== 201) {
    const data = JSON.parse(res.getContentText());
    throw new Error(`GitHub commit エラー (${code}): ${data.message}`);
  }
}

// ==========================================
// 失敗通知
// ==========================================

function notifyAdminOnFailure(slug, errorMessage) {
  const adminEmail = PropertiesService.getScriptProperties().getProperty('ADMIN_EMAIL')
                     || 'kengo1983@gmail.com';
  const now = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm');

  try {
    GmailApp.sendEmail(
      adminEmail,
      `[歴史HP] ${slug} の自動 publish に失敗しました`,
      `処理日時: ${now}\nSlug: ${slug}\n\nエラー内容:\n${errorMessage}\n\nGAS ログを確認してください（実行 > ログ > 最近の実行）`
    );
    Logger.log(`通知メールを ${adminEmail} に送信しました`);
  } catch (e) {
    Logger.log(`メール送信エラー: ${e.message}`);
  }
}
