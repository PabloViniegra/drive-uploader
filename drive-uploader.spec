# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for drive-uploader.

Build with:
    pyinstaller build/drive-uploader.spec

Produces dist/drive-uploader (or drive-uploader.exe on Windows), a
self-contained console-mode binary bundling the application, the
.env.example template, and the Google API client modules that perform
dynamic imports.
"""
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden = []
hidden += collect_submodules("src.bootstrap")
hidden += collect_submodules("src.shared")
hidden += collect_submodules("src.domain")
hidden += collect_submodules("src.application")
hidden += collect_submodules("src.infrastructure")
hidden += collect_submodules("googleapiclient")
hidden += collect_submodules("google")
hidden += collect_submodules("google.auth")
hidden += collect_submodules("google.auth.transport")
hidden += collect_submodules("google.oauth2")
hidden += collect_submodules("google_auth_oauthlib")
hidden += collect_submodules("httplib2")
hidden += collect_submodules("uritemplate")
hidden += collect_submodules("watchdog")
hidden += collect_submodules("watchdog.events")
hidden += collect_submodules("watchdog.observers")
hidden += collect_submodules("watchdog.utils")
# PEP 420 implicit namespace packages are bundled as data, which causes
# PyInstaller's static analysis to skip the stdlib imports inside those
# files. List them explicitly so they end up in the PYZ archive.
hidden += [
    "collections",
    "dataclasses",
    "datetime",
    "enum",
    "json",
    "logging",
    "os",
    "pathlib",
    "signal",
    "socket",
    "sqlite3",
    "sys",
    "threading",
    "time",
    "typing",
    "urllib",
    "uuid",
]

# An empty placeholder makes PyInstaller treat `src` as a real package
# (rather than an implicit namespace) so submodules resolve at runtime.
hidden += ["src"]

# Bundle the entire src/ tree as data so Python's implicit namespace
# package machinery can resolve `src.*` imports against _MEIPASS/src/
# at runtime.

a = Analysis(
    ["src/bootstrap/main.py"],
    pathex=["src"],
    binaries=[],
    datas=[(".env.example", "."), ("src", "src")],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["build/runtime_hook.py"],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="drive-uploader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)