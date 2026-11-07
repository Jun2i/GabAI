Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Check and start mysqld if needed
WshShell.Run "cmd /c tasklist /fi ""imagename eq mysqld.exe"" 2>nul | findstr /i mysqld >nul || start """" /b ""C:\xampp\mysql\bin\mysqld.exe"" --bind-address=127.0.0.1 --port=3307", 0, True

' Start Django in background silently
WshShell.Run "python manage.py runserver 0.0.0.0:8000 --noreload --skip-checks", 0, False

' Open browser to localhost immediately
WshShell.Run "http://localhost:8000/", 1, False

