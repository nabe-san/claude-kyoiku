@echo off
chcp 65001 >nul

cd /d "C:\projects\claude-kaihatsu\rekishi-hp"
git pull

cd /d "C:\projects\claude-kaihatsu\Obsidian連携"
python import_citations.py

echo 完了しました。
pause