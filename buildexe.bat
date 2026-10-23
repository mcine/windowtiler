py -m PyInstaller --onefile --icon=icon.ico --name WindowTiler app.py
Copy-Item config.yaml dist\
Copy-Item -Recurse layouts dist\
