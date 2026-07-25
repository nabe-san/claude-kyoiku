@echo off
chcp 65001 >nul

set LOGFILE=C:\projects\claude-kaihatsu\Obsidian連携\sync_citations.log

echo %date% %time% ジョブ開始 >> "%LOGFILE%"

cd /d "C:\projects\claude-kaihatsu\rekishi-hp"
git pull >> "%LOGFILE%" 2>&1

cd /d "C:\projects\claude-kaihatsu\Obsidian連携"
python import_citations.py >> "%LOGFILE%" 2>&1

echo %date% %time% ジョブ終了 >> "%LOGFILE%"
echo 完了しました。