@echo off
chcp 932 >nul

python app_main_base_pc_dir.py
if %errorlevel% neq 0 (
    echo.
    echo 【エラー】起動に失敗しました。
    echo setup.bat を実行済みか、ファイル名が正しいか確認してください。
    echo.
    pause
)
