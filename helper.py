#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Privileged host changes only. No fingerprint, key or firmware access."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile

SOURCE_REVISION = '184e9aa1b47c4d6da19c7b95be85d0a7f55a95b2'
SOURCE_SHA256 = '5337c96f4b0c3a10be5bbb592e88077476e0c9d0a7857e370e86965f441b64ba'
LEGACY_SHA256 = '8c3ce5775b935638cf8bd2af35f9b257a6a0e0e1113c7a1aa02e28162ef1cb3b'
DROP_CONTENT = '[Service]\nEnvironment=LD_LIBRARY_PATH=/opt/goodix-5125-ubuntu/lib\n'
PACKAGES = ['build-essential','meson','ninja-build','libglib2.0-dev',
            'libgusb-dev','libusb-1.0-0-dev','libssl-dev','libjson-glib-dev',
            'fprintd','libpam-fprintd','usbutils','gnome-control-center']

def run(*args):
    subprocess.run(list(args), check=True, env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','DEBIAN_FRONTEND':'noninteractive'})

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pam_enabled(root):
    return any(line.lstrip().startswith('auth') and 'pam_fprintd.so' in line
               for line in (root/'etc/pam.d/common-auth').read_text().splitlines())

def trusted(path, directory=False):
    s = path.lstat()
    if s.st_uid != 0 or s.st_gid != 0 or s.st_mode & 0o022 or not (
        stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode)):
        raise RuntimeError('Unexpected ownership, type or permissions: ' + str(path))

class Host:
    def __init__(self, root=Path('/')):
        self.root = root
        self.dest = root/'opt/goodix-5125-ubuntu'
        self.drop = root/'etc/systemd/system/fprintd.service.d/90-goodix-5125-ubuntu.conf'
        self.state = root/'var/lib/fprint/goodix-5125-state-v2'
    def validate_existing(self):
        present = self.dest.exists() or self.dest.is_symlink()
        override = self.drop.exists() or self.drop.is_symlink()
        if present != override:
            raise RuntimeError('Partial installation detected; preserve it and inspect manually.')
        if not present:
            return None
        trusted(self.dest, True)
        trusted(self.drop)
        if self.drop.read_text() != DROP_CONTENT:
            raise RuntimeError('A different service override is present.')
        library = self.dest/'lib/libfprint-2.so.2.0.0'
        trusted(self.dest/'lib', True)
        trusted(library)
        link = self.dest/'lib/libfprint-2.so.2'
        if not link.is_symlink() or os.readlink(link) != library.name:
            raise RuntimeError('Unexpected library link.')
        receipt = self.dest/'receipt.json'
        if receipt.exists():
            trusted(receipt)
            data = json.loads(receipt.read_text())
            if data.get('manager') != 'goodix-ubuntu-easy' or data.get('library_sha256') != digest(library):
                raise RuntimeError('Installation receipt mismatch.')
            expected = {'lib','receipt.json','helper.py'}
            trusted(self.dest/'helper.py')
            if data.get('helper_sha256') != digest(self.dest/'helper.py'):
                raise RuntimeError('Recovery helper differs from its receipt.')
        else:
            if digest(library) != LEGACY_SHA256:
                raise RuntimeError('Unrecognized existing driver; will not overwrite it.')
            data = {'pam_was_enabled': pam_enabled(self.root)}
            expected = {'lib'}
        if {p.name for p in self.dest.iterdir()} != expected or {p.name for p in (self.dest/'lib').iterdir()} != {library.name,link.name}:
            raise RuntimeError('Unexpected files in driver directory; preserving them.')
        return data
    def _state(self):
        if self.state.exists() or self.state.is_symlink():
            trusted(self.state, True)
            if stat.S_IMODE(self.state.stat().st_mode) != 0o700:
                raise RuntimeError('Pairing directory must have mode 0700.')
        else:
            if not self.state.parent.exists():
                trusted(self.state.parent.parent, True)
                self.state.parent.mkdir(mode=0o700)
            trusted(self.state.parent, True)
            self.state.mkdir(mode=0o700)
    def activate(self, build):
        previous = self.validate_existing()
        build = Path(build)
        if build.is_symlink() or not build.is_absolute():
            raise RuntimeError('Invalid build directory.')
        info = json.loads((build/'build.json').read_text())
        candidate = build/'build/libfprint/libfprint-2.so.2.0.0'
        caller = int(os.environ.get('PKEXEC_UID', os.environ.get('SUDO_UID','0')))
        s = candidate.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_uid not in (caller, 0):
            raise RuntimeError('Invalid build ownership/type.')
        contents = candidate.read_bytes()
        if contents[:6] != b'\x7fELF\x02\x01' or contents[18:20] != b'\x3e\x00':
            raise RuntimeError('Expected an x86-64 ELF library.')
        if info.get('source_revision') != SOURCE_REVISION or info.get('source_sha256') != SOURCE_SHA256 or hashlib.sha256(contents).hexdigest() != info.get('library_sha256'):
            raise RuntimeError('Build/source checksum mismatch.')
        self._state()
        trusted(self.dest.parent, True)
        enabled_now = pam_enabled(self.root)
        enabled_before = previous.get('pam_was_enabled', False) if previous else enabled_now
        stage = Path(tempfile.mkdtemp(prefix='.goodix-stage-',dir=self.dest.parent))
        stage.chmod(0o755)
        backup = stage.with_name(stage.name + '-previous')
        swapped = False
        stopped = False
        try:
            (stage/'lib').mkdir(mode=0o755)
            target = stage/'lib/libfprint-2.so.2.0.0'
            target.write_bytes(contents)
            target.chmod(0o644)
            (stage/'lib/libfprint-2.so.2').symlink_to(target.name)
            shutil.copyfile(Path(__file__), stage/'helper.py')
            (stage/'helper.py').chmod(0o644)
            info.update(manager='goodix-ubuntu-easy',pam_was_enabled=enabled_before,
                        helper_sha256=digest(stage/'helper.py'))
            (stage/'receipt.json').write_text(json.dumps(info,indent=2)+'\n')
            (stage/'receipt.json').chmod(0o644)
            run('systemctl','stop','fprintd.service')
            stopped = True
            if previous:
                self.dest.rename(backup)
            stage.rename(self.dest)
            swapped = True
            self.drop.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
            self.drop.write_text(DROP_CONTENT)
            self.drop.chmod(0o644)
            # GNOME already has a separate gdm-fingerprint path. Avoid a second
            # Claim from gdm-password through common-auth; retain password auth.
            run('pam-auth-update','--disable','fprintd')
            run('systemctl','daemon-reload')
            run('systemctl','start','fprintd.service')
        except BaseException:
            if swapped:
                shutil.rmtree(self.dest)
            if backup.exists():
                backup.rename(self.dest)
            if previous:
                self.drop.write_text(DROP_CONTENT)
            elif self.drop.exists():
                self.drop.unlink()
            if stopped:
                run('pam-auth-update','--enable' if enabled_now else '--disable','fprintd')
                run('systemctl','daemon-reload')
                run('systemctl','start','fprintd.service')
            raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        if backup.exists():
            shutil.rmtree(backup)
        print('INSTALL=PASS; FIRMWARE_WRITES=NO; SENSOR_ACCESS=NO',flush=True)
    def remove(self):
        data = self.validate_existing()
        if data is None:
            print('Nothing installed.'); return
        enabled_now = pam_enabled(self.root)
        run('systemctl','stop','fprintd.service')
        self.drop.unlink()
        try:
            run('pam-auth-update','--enable' if data.get('pam_was_enabled') else '--disable','fprintd')
            run('systemctl','daemon-reload')
            run('systemctl','start','fprintd.service')
        except BaseException:
            self.drop.write_text(DROP_CONTENT)
            run('pam-auth-update','--enable' if enabled_now else '--disable','fprintd')
            run('systemctl','daemon-reload')
            run('systemctl','start','fprintd.service')
            raise
        shutil.rmtree(self.dest)
        print('REMOVE=PASS; ENROLLED_PRINTS_AND_PAIRING_PRESERVED=YES',flush=True)

def preflight():
    release = platform.freedesktop_os_release()
    if release.get('ID') != 'ubuntu' or release.get('VERSION_ID') != '26.10' or platform.machine() != 'x86_64':
        raise RuntimeError('Only Ubuntu 26.10 x86-64 is supported.')
    if 'pam_fprintd.so' not in Path('/etc/pam.d/gdm-fingerprint').read_text():
        raise RuntimeError('Expected GNOME/GDM fingerprint configuration is absent.')
    if '27c6:5125' not in subprocess.check_output(['lsusb','-d','27c6:5125'],text=True):
        raise RuntimeError('The required Goodix 27c6:5125 device was not found.')
    env = subprocess.check_output(['systemctl','show','fprintd.service','-p','Environment','--value'],text=True)
    for item in env.split():
        if 'LD_LIBRARY_PATH=' in item and item.strip('"') != 'LD_LIBRARY_PATH=/opt/goodix-5125-ubuntu/lib':
            raise RuntimeError('Another custom fingerprint library is configured.')

def dependencies():
    # Use the configured official Ubuntu source over HTTPS without editing it.
    source = Path('/etc/apt/sources.list.d/ubuntu.sources')
    with tempfile.TemporaryDirectory(prefix='goodix-apt-',dir='/run') as folder:
        options = []
        if source.is_file():
            text = source.read_text().replace('http://archive.ubuntu.com/ubuntu','https://archive.ubuntu.com/ubuntu').replace('http://security.ubuntu.com/ubuntu','https://security.ubuntu.com/ubuntu')
            temporary = Path(folder)/'ubuntu.sources'
            temporary.write_text(text)
            options = ['-o','Dir::Etc::sourcelist='+str(temporary),'-o','Dir::Etc::sourceparts=-']
        run('apt-get',*options,'install','--no-upgrade','-y',*PACKAGES)

def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run this helper through pkexec or sudo.')
    if len(sys.argv) < 2 or sys.argv[1] not in ('dependencies','activate','remove'):
        raise RuntimeError('Expected dependencies, activate BUILD_DIRECTORY, or remove.')
    action = sys.argv[1]
    if len(sys.argv) != (3 if action == 'activate' else 2):
        raise RuntimeError('Unexpected arguments.')
    with open('/run/lock/goodix-ubuntu-easy.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if action != 'remove':
            preflight()
        host = Host()
        if action == 'dependencies':
            host.validate_existing(); dependencies()
        elif action == 'activate':
            host.activate(Path(sys.argv[2]))
        else:
            host.remove()

if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('ERROR:',error,file=sys.stderr);sys.exit(1)
