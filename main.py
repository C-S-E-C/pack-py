from os import system as cmd
import json
import sys

with open("config.json",encoding="utf-8") as f:
   dic = json.load(f)
cmd("pip install -r project/requirements.txt")
cmd("pip install pyinstaller")
print(sys.platform)
if sys.platform.startswith('linux'):
    sysname="linux"
elif sys.platform.startswith('darwin'):
    sysname="mac"
elif sys.platform.startswith('win32'):
    sysname="win"
dic = dic[sysname]
if dic["console"]["singlefile"]:
  cmd("pyinstaller project/main.py")
if dic["windowed"]["singlefile"]:
  cmd("pyinstaller -w -F project/main.py")
if dic["console"]["multifile"]:
  cmd("pyinstaller -F project/main.py")
if dic["windowed"]["multifile"]:
  cmd("pyinstaller -w project/main.py")
