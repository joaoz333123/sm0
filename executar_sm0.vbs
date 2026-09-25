Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

pythonwPath = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe")
If fso.FileExists(pythonwPath) Then
    WshShell.Run """" & pythonwPath & """ main.py", 0, False
Else
    WshShell.Run "pythonw.exe main.py", 0, False
End If
