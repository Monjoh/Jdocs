# -*- mode: python ; coding: utf-8 -*-
# jDocs PyInstaller spec file

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # python-docx
        'docx',
        'docx.document',
        'docx.opc',
        'docx.opc.part',
        'docx.opc.constants',
        'docx.opc.package',
        'docx.opc.pkgreader',
        'docx.oxml',
        'docx.oxml.ns',
        'docx.oxml.parser',
        'lxml',
        'lxml.etree',
        'lxml._elementpath',
        # openpyxl
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.workbook',
        'openpyxl.reader',
        'openpyxl.reader.excel',
        'openpyxl.utils',
        'openpyxl.utils.exceptions',
        'openpyxl.xml',
        'openpyxl.xml.functions',
        # python-pptx
        'pptx',
        'pptx.util',
        'pptx.oxml',
        'pptx.oxml.ns',
        # Pillow
        'PIL',
        'PIL.Image',
        'PIL.ExifTags',
        'PIL.JpegImagePlugin',
        'PIL.PngImagePlugin',
        'PIL.GifImagePlugin',
        'PIL.BmpImagePlugin',
        'PIL.TiffImagePlugin',
        # stdlib used by app
        'sqlite3',
        'csv',
        'json',
        'shutil',
        'platform',
        'io',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Unused Qt modules (save significant space)
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtNetwork',
        'PyQt5.QtBluetooth',
        'PyQt5.QtNfc',
        'PyQt5.QtPositioning',
        'PyQt5.QtLocation',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtSql',
        'PyQt5.QtSvg',
        'PyQt5.QtTest',
        'PyQt5.QtXml',
        'PyQt5.QtXmlPatterns',
        'PyQt5.QtHelp',
        'PyQt5.QtOpenGL',
        'PyQt5.QtQuick',
        'PyQt5.QtQml',
        'PyQt5.QtDBus',
        'PyQt5.QtDesigner',
        # Development/testing tools
        'pytest',
        'unittest',
        'tkinter',
        '_tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='jDocs',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No terminal window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='jDocs',
)

# macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='jDocs.app',
        bundle_identifier='com.jdocs.app',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
