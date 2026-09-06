@echo off
chcp 65001 >nul

set LOGFILE=C:\projects\claude-kaihatsu\Obsidian連携\watch_chat_exports.log

echo %date% %time% ジョブ開始 >> "%LOGFILE%"

cd /d "C:\projects\claude-kaihatsu\Obsidian連携"
python watch_and_import_chat_exports.py >> "%LOGFILE%" 2>&1

echo %date% %time% ジョブ終了 >> "%LOGFILE%"
echo 完了しました。
