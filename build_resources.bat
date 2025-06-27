@echo off
echo --- PixelForge Resource Builder ---

echo [1/4] Checking for a temporary build environment...
if not exist .\.build_venv\ (
    echo      -> Build environment not found. Creating one...
    py -3.12 -m venv .build_venv
) else (
    echo      -> Found existing build environment.
)

echo [2/4] Activating build environment and installing tools...
call .\.build_venv\Scripts\activate.bat
pip install PySide6==6.7.0 > nul

echo [3/4] Compiling resources.qrc using PySide6-rcc...
pyside6-rcc resources.qrc -o resources_rc.py

echo [4/4] Deactivating build environment.
call .\.build_venv\Scripts\deactivate.bat

echo --- Build Complete ---
echo resources_rc.py has been generated. You may need to manually edit it.
pause