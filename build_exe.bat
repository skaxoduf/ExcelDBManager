@echo off
echo Building ExcelDBManager...

:: PyInstaller 실행
pyinstaller --noconfirm --onefile --windowed --name "ExcelDBManager" --clean --hidden-import=pyodbc --hidden-import=watchdog --icon="logo.ico" --exclude-module=selenium --exclude-module=tkinter --exclude-module=matplotlib --exclude-module=scipy --exclude-module=ipython --exclude-module=notebook --exclude-module=numba --exclude-module=lxml main.py

:: 설정 파일 및 이미지 복사
echo Copying configuration files...
copy config.ini dist\config.ini
copy secret.key dist\secret.key
copy src\assets\logo.png dist\logo.png

echo Build complete! Executable is in the 'dist' folder.
pause
