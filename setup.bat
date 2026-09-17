@echo off
chcp 65001 >nul
echo ==========================================
echo  HVOS (PC direct display) setup
echo ==========================================

pip --version >nul 2>&1
if %errorlevel% == 0 (
    pip install pyautogui keyboard pillow google-genai
    goto SUCCESS
)

python -m pip --version >nul 2>&1
if %errorlevel% == 0 (
    python -m pip install pyautogui keyboard pillow google-genai
    goto SUCCESS
)

py -m pip --version >nul 2>&1
if %errorlevel% == 0 (
    py -m pip install pyautogui keyboard pillow google-genai
    goto SUCCESS
)

:ERROR
echo.
echo [ERROR] Python or pip was not found.
echo 1. Restart your PC and try again.
echo 2. Reinstall Python and check "Add python.exe to PATH".
echo.
pause
exit

:SUCCESS
echo.
echo ------------------------------------------
echo Setup completed!
echo ------------------------------------------
pause