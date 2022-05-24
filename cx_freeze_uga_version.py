import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
# "packages": ["os"] is used as example only
build_exe_options = {"packages": ["os"], "excludes": [], "includes": ["PySimpleGUI","loguru","lxml","paramiko","scp","asnake","requests"]}

# base="Win32GUI" should be used only for Windows GUI app
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="ASpace_Batch_Export",
    version="0.1",
    description="Aspace Batch Export",
    options={"build_exe": build_exe_options},
    executables=[Executable("as_xtf_GUI.py", base=base, targetName="ASpace_Batch_Export_vRELEASEVERSIONNUMBERNODOTS-UGA.exe", icon="thumbnail.ico")],
)
