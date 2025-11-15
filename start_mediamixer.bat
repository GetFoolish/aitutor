@echo off
echo Starting MediaMixer Service...
echo.

cd /d "%~dp0"
cd MediaMixer

echo Activating virtual environment...
call ..\venv\Scripts\activate.bat

echo.
echo Starting MediaMixer on ports 8765 and 8766...
echo Press Ctrl+C to stop
echo.

python media_mixer.py

pause

