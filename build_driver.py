#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build pinned, bundled source as an ordinary user. Never accesses USB."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tarfile

REVISION = '184e9aa1b47c4d6da19c7b95be85d0a7f55a95b2'
SOURCE_SHA256 = '5337c96f4b0c3a10be5bbb592e88077476e0c9d0a7857e370e86965f441b64ba'
VERSION = '0.1.0'

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def extract_source(archive, destination):
    if sha256(archive) != SOURCE_SHA256:
        raise RuntimeError('Source archive checksum does not match the pinned release.')
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            if not (member.isfile() or member.isdir()):
                raise RuntimeError('Unexpected link or special file in source archive.')
            parts = Path(member.name).parts
            if not parts or parts[0] != 'goodix-source' or '..' in parts or member.name.startswith('/'):
                raise RuntimeError('Unsafe source archive path.')
        source.extractall(destination, filter='data')
    return destination / 'goodix-source'

def build(package, output):
    if os.geteuid() == 0:
        raise RuntimeError('Compile as your ordinary user, never as root.')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    root = extract_source(package / 'vendor/goodix-source.tar.gz', output)
    spec = importlib.util.spec_from_file_location('native', root / 'production/build-chicago-native.py')
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    def capture(*args):
        return subprocess.check_output([str(a) for a in args], text=True)
    native_work = output / 'native-work'
    native_work.mkdir()
    archive, include, _ = native.build_native(root, native_work, capture)
    meson = output / 'build'
    subprocess.run([
        'meson', 'setup', str(meson),
        str(root / 'reference/libfprint-fedora44-1.94.100/source'),
        '--prefix=/usr', '--libdir=lib/x86_64-linux-gnu', '--buildtype=release',
        '--wrap-mode=nodownload', '-Ddrivers=goodix_27c6_5125',
        '-Dintrospection=false', '-Ddoc=false', '-Dinstalled-tests=false',
        '-Dudev_rules=disabled', '-Dudev_hwdb=disabled',
        '-Dgoodix_production_minimal=true', '-Dgoodix_chicago=true',
        '-Dgoodix_chicago_native_archive=' + str(archive),
        '-Dgoodix_chicago_native_include=' + str(include),
        '-Dc_args=-DGOODIX_PRODUCTION_FPRINTD_ACTION_PROFILE',
    ], check=True)
    subprocess.run(['meson','compile','-C',str(meson),'fprint-2'], check=True)
    library = meson / 'libfprint/libfprint-2.so.2.0.0'
    env = dict(os.environ, LD_LIBRARY_PATH=str(library.parent))
    for executable in (str(library), '/usr/libexec/fprintd'):
        result = subprocess.run(['ldd','-r',executable], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        print(result.stdout, flush=True)
        if 'undefined symbol' in result.stdout or 'not found' in result.stdout:
            raise RuntimeError('Library compatibility check failed; nothing was installed.')
        if executable.endswith('/fprintd') and str(library.parent) not in result.stdout:
            raise RuntimeError('fprintd did not resolve the newly built library.')
    manifest = {'version': VERSION, 'source_revision': REVISION,
                'source_sha256': SOURCE_SHA256, 'library_sha256': sha256(library)}
    (output / 'build.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('BUILD_AND_ABI_CHECK=PASS; DEVICE_ACCESS=NO', flush=True)
    return output
