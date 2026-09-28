# PyInstaller spec: the engine frozen in folder mode as the desktop app's
# sidecar. Build with: uv run pyinstaller scripts/sidecar.spec
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

REPO = os.path.dirname(SPECPATH)

a = Analysis(
    [os.path.join(REPO, "src", "rentczecher", "cli", "main.py")],
    pathex=[os.path.join(REPO, "src")],
    # The gazetteer, the SQL migrations and the location data are package
    # files, not imports, so PyInstaller only ships them when told.
    datas=collect_data_files("rentczecher"),
    # uvicorn picks its event loop and protocol implementations by string at
    # runtime, invisible to PyInstaller's import scan.
    hiddenimports=collect_submodules("uvicorn"),
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="rentczecher-sidecar",
    # A console-less build on Windows has no stdout, and the shell reads the
    # PORT line from it. The shell hides the console window when spawning.
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, name="rentczecher-sidecar")
