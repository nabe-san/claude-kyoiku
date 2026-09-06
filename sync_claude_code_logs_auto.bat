@echo off
chcp 65001 >nul

set LOGFILE=C:\projects\claude-kaihatsu\Obsidian連携\sync_claude_code_logs.log

echo %date% %time% ジョブ開始 >> "%LOGFILE%"

cd /d "C:\projects\claude-kaihatsu\Obsidian連携"
python import_claude_code_logs.py >> "%LOGFILE%" 2>&1

echo %date% %time% ジョブ終了 >> "%LOGFILE%"
echo 完了しました。
