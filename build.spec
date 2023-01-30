# -*- mode: python ; coding: utf-8 -*-
import os.path
from pathlib import Path
import shutil
import sys
import tomllib

def domichess_version():
	"""
	Get the current version of DomiChess from the pyproject.toml file. It assumes the use of Poetry.
	"""
	pyproject_path = Path(__name__).resolve().parent / Path("pyproject.toml")
	if pyproject_path.is_file():
		try:
			with pyproject_path.open('rb') as pyproject_file:
				pyproject_toml = tomllib.load(pyproject_file)
			return pyproject_toml['tool']['poetry']['version']
		except tomllib.TOMLDecodeError:
			return
	else:
		return

def domichess_name():
	"""
	Get the name of DomiChess app from the pyproject.toml file. It assumes the use of Poetry.
	"""
	pyproject_path = Path(__name__).resolve().parent / Path("pyproject.toml")
	if pyproject_path.is_file():
		try:
			with pyproject_path.open('rb') as pyproject_file:
				pyproject_toml = tomllib.load(pyproject_file)
			return pyproject_toml['tool']['poetry']['name']
		except tomllib.TOMLDecodeError:
			return
	else:
		return

def include_cairodll():
	"""
	Returns a set to be included in the list for the `binaries` parameter, for getting the correct version of cairo.dll file, regarding wether the system is 32 or 64 bit.
	"""
	if sys.maxsize > 2**32: # 64 bit
		return ('cairo_64bit.dll','.')
	else: # 32 bit
		return ('cairo_32bit.dll','.')

block_cipher = None

binary_files = [include_cairodll()]

data_files = [
			('domichess/resources', 'domichess/resources'),
			('Tierce Sources and Licenses', 'Tierce Sources and Licenses'),
			('icons', 'icons'),
			('pyproject.toml', '.')
			]

a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=binary_files,
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=False,
    name=f'{domichess_name()}_{domichess_version()}_{"64bit" if sys.maxsize > 2**32 else "32bit"}',
	icon=[
		str(Path('icons') / Path('chess_512px.ico')),
		str(Path('icons') / Path('chess_256px.ico')),
		str(Path('icons') / Path('chess_128px.ico')),
		str(Path('icons') / Path('chess_96px.ico')),
		str(Path('icons') / Path('chess_72px.ico')),
		str(Path('icons') / Path('chess_64px.ico')),
		str(Path('icons') / Path('chess_32px.ico'))
		],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

