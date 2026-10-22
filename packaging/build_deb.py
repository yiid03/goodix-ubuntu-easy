#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a GUI installer package. No package scripts change host authentication."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_driver import VERSION
ROOT=Path(__file__).resolve().parents[1]
output=ROOT/'dist';output.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='goodix-deb-') as temporary:
    stage=Path(temporary)
    app=stage/'usr/lib/goodix-ubuntu-easy';app.mkdir(parents=True)
    for name in ('easy.py','helper.py','build_driver.py','README.md','README.tr.md','LICENSE','THIRD_PARTY.md'):
        shutil.copyfile(ROOT/name,app/name)
    shutil.copytree(ROOT/'vendor',app/'vendor')
    for p in app.rglob('*'):p.chmod(0o755 if p.is_dir() else 0o644)
    binary=stage/'usr/bin/goodix-ubuntu-easy';binary.parent.mkdir(parents=True)
    binary.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/lib/goodix-ubuntu-easy/easy.py "$@"\n');binary.chmod(0o755)
    desktop=stage/'usr/share/applications/goodix-ubuntu-easy.desktop';desktop.parent.mkdir(parents=True)
    desktop.write_text('''[Desktop Entry]
Type=Application
Name=Goodix Fingerprint Setup
Name[tr]=Goodix Parmak İzi Kurulumu
Comment=Install the community driver for Goodix 27c6:5125 on Ubuntu GNOME
Exec=goodix-ubuntu-easy
Icon=fingerprint
Terminal=false
Categories=Settings;HardwareSettings;
Keywords=fingerprint;goodix;parmak;izi;
''')
    desktop.chmod(0o644)
    control=stage/'DEBIAN';control.mkdir()
    (control/'control').write_text(f'''Package: goodix-ubuntu-easy
Version: {VERSION}
Architecture: amd64
Maintainer: Goodix Ubuntu Easy contributors <noreply@example.invalid>
Depends: python3 (>= 3.12), python3-gi, gir1.2-gtk-4.0, pkexec, usbutils, fprintd, libpam-fprintd, gnome-control-center
Section: utils
Priority: optional
Description: Experimental Goodix 27c6:5125 installer for Ubuntu 26.10 GNOME
 Builds pinned bundled community source locally and activates an isolated driver.
 Fingerprint enrollment uses GNOME Settings. No firmware flashing.
''')
    stage.chmod(0o755)
    for path in stage.rglob('*'):
        if path.is_dir():path.chmod(0o755)
        elif path != binary:path.chmod(0o644)
    subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(output/f'goodix-ubuntu-easy_{VERSION}_amd64.deb')],check=True)
