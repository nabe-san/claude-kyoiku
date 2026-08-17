// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 調べものログ 設定
// 秘密情報（ANTHROPIC_API_KEY, SHARED_TOKEN）はここに書かず、
// 「プロジェクトの設定」→「スクリプト プロパティ」に登録すること
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const CONFIG = {
  QUEUE_SHEET_ID:   'YOUR_SPREADSHEET_ID',       // 中継スプレッドシートのID
  QUEUE_SHEET_NAME: 'キュー',
  DIGEST_TO:        'YOUR_EMAIL@gmail.com',      // 週次ダイジェストの送信先
  CLAUDE_MODEL:     'claude-opus-5',
};

const COL = {
  TIMESTAMP: 0,
  QUERY:     1,
  STATUS:    2,
  NOTE:      3,
};
