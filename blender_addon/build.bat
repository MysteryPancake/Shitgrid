:: This part should be automated whenever an asset updates
ECHO off
SET /p asset="Type an asset name: "

:: This shouldn't be hardcoded
"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe" -b --python-use-system-env -P "clean.py" -P "build.py" -- --asset "%asset%"