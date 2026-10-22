# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import helper
import build_driver
import easy

class Transactions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for path in ('opt','var/lib/fprint','etc/pam.d','etc/systemd/system'):
            (self.root/path).mkdir(parents=True,exist_ok=True)
        (self.root/'etc/pam.d/common-auth').write_text('auth required pam_unix.so\n')
        self.host=helper.Host(self.root)
        self.commands=[]
        self.runner=patch.object(helper,'run',side_effect=lambda *a:self.commands.append(a));self.runner.start()
        # Fake host files belong to the test user. Never request root or use /.
        self.trust=patch.object(helper,'trusted');self.trust.start()
        self.env=patch.dict(os.environ,{'PKEXEC_UID':str(os.getuid())});self.env.start()
        self.built=self.root/'candidate';(self.built/'build/libfprint').mkdir(parents=True)
        self.library=self.built/'build/libfprint/libfprint-2.so.2.0.0'
        self.contents=b'\x7fELF\x02\x01'+b'\0'*12+b'\x3e\x00'+b'local-test-only'
        self.library.write_bytes(self.contents)
        self.manifest={'source_revision':helper.SOURCE_REVISION,'source_sha256':helper.SOURCE_SHA256,
                       'library_sha256':helper.digest(self.library),'version':'0.1.0'}
        (self.built/'build.json').write_text(json.dumps(self.manifest))
    def tearDown(self):
        self.env.stop();self.trust.stop();self.runner.stop();self.tmp.cleanup()
    def test_install_and_remove_preserve_keys_and_password(self):
        self.host.activate(self.built)
        secret=self.host.state/'retained-key';secret.write_bytes(b'private-test-fixture')
        self.assertEqual(self.host.drop.read_text(),helper.DROP_CONTENT)
        self.assertEqual(self.host.validate_existing()['manager'],'goodix-ubuntu-easy')
        self.host.remove()
        self.assertFalse(self.host.dest.exists());self.assertFalse(self.host.drop.exists())
        self.assertEqual(secret.read_bytes(),b'private-test-fixture')
        self.assertIn('pam_unix.so',(self.root/'etc/pam.d/common-auth').read_text())
        self.assertIn(('pam-auth-update','--disable','fprintd'),self.commands)
    def test_first_install_failure_rolls_back(self):
        failed=False
        def run(*args):
            nonlocal failed
            self.commands.append(args)
            if args==('systemctl','start','fprintd.service') and not failed:
                failed=True;raise RuntimeError('simulated start failure')
        with patch.object(helper,'run',side_effect=run):
            with self.assertRaisesRegex(RuntimeError,'simulated'):self.host.activate(self.built)
        self.assertFalse(self.host.dest.exists());self.assertFalse(self.host.drop.exists())
        self.assertEqual(list((self.root/'opt').iterdir()),[])
    def test_update_failure_restores_existing_library_and_receipt(self):
        self.host.activate(self.built)
        original=(self.host.dest/'receipt.json').read_bytes()
        failed=False
        def run(*args):
            nonlocal failed
            if args==('systemctl','start','fprintd.service') and not failed:
                failed=True;raise RuntimeError('simulated start failure')
        with patch.object(helper,'run',side_effect=run):
            with self.assertRaises(RuntimeError):self.host.activate(self.built)
        self.assertEqual((self.host.dest/'receipt.json').read_bytes(),original)
        self.assertEqual((self.host.dest/'lib/libfprint-2.so.2.0.0').read_bytes(),self.contents)
        self.host.validate_existing()
    def test_refuses_partial_foreign_install_before_host_mutation(self):
        self.host.dest.mkdir();(self.host.dest/'unrelated').write_text('keep')
        with self.assertRaisesRegex(RuntimeError,'Partial'):self.host.activate(self.built)
        self.assertEqual(self.commands,[])
        self.assertEqual((self.host.dest/'unrelated').read_text(),'keep')
    def test_rejects_tampered_build_before_host_mutation(self):
        self.library.write_bytes(self.contents+b'tampered')
        with self.assertRaisesRegex(RuntimeError,'checksum'):self.host.activate(self.built)
        self.assertEqual(self.commands,[])
    def test_foreign_file_blocks_remove_and_update(self):
        self.host.activate(self.built);(self.host.dest/'unrelated').write_text('keep')
        before=list(self.commands)
        with self.assertRaisesRegex(RuntimeError,'Unexpected files'):self.host.remove()
        self.assertEqual(self.commands,before)
    def test_remove_failure_restores_override(self):
        self.host.activate(self.built)
        failed=False
        def run(*args):
            nonlocal failed
            if args==('systemctl','start','fprintd.service') and not failed:
                failed=True;raise RuntimeError('simulated start failure')
        with patch.object(helper,'run',side_effect=run):
            with self.assertRaises(RuntimeError):self.host.remove()
        self.assertEqual(self.host.drop.read_text(),helper.DROP_CONTENT)
        self.host.validate_existing()
    def test_restores_preexisting_pam_preference(self):
        (self.root/'etc/pam.d/common-auth').write_text('auth required pam_fprintd.so\nauth required pam_unix.so\n')
        self.host.activate(self.built);self.host.remove()
        self.assertIn(('pam-auth-update','--enable','fprintd'),self.commands)
    def test_recognizes_only_the_known_manual_predecessor(self):
        (self.host.dest/'lib').mkdir(parents=True)
        lib=self.host.dest/'lib/libfprint-2.so.2.0.0';lib.write_bytes(self.contents)
        (lib.parent/'libfprint-2.so.2').symlink_to(lib.name)
        self.host.drop.parent.mkdir(parents=True,exist_ok=True);self.host.drop.write_text(helper.DROP_CONTENT)
        with self.assertRaisesRegex(RuntimeError,'Unrecognized'):self.host.validate_existing()
        with patch.object(helper,'LEGACY_SHA256',helper.digest(lib)):
            self.host.activate(self.built)
        self.assertEqual(self.host.validate_existing()['manager'],'goodix-ubuntu-easy')
    def test_tampered_recovery_helper_blocks_remove(self):
        self.host.activate(self.built)
        (self.host.dest/'helper.py').write_text('modified')
        with self.assertRaisesRegex(RuntimeError,'Recovery helper'):self.host.remove()

class SourceArchive(unittest.TestCase):
    def test_real_bundled_archive_is_pinned(self):
        package=Path(__file__).resolve().parents[1]
        self.assertEqual(build_driver.sha256(package/'vendor/goodix-source.tar.gz'),build_driver.SOURCE_SHA256)
    def test_tampered_archive_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.tar.gz';p.write_bytes(b'not the source')
            with self.assertRaisesRegex(RuntimeError,'checksum'):build_driver.extract_source(p,Path(temp))
    def test_traversal_rejected_even_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.tar.gz'
            with tarfile.open(p,'w:gz') as archive:
                member=tarfile.TarInfo('goodix-source/../../escaped');member.size=1
                archive.addfile(member,io.BytesIO(b'x'))
            with patch.object(build_driver,'SOURCE_SHA256',build_driver.sha256(p)):
                with self.assertRaisesRegex(RuntimeError,'Unsafe'):build_driver.extract_source(p,Path(temp))
            self.assertFalse((Path(temp).parent/'escaped').exists())

class Compatibility(unittest.TestCase):
    def test_foreign_os_is_not_compatible(self):
        with patch.object(easy.platform,'freedesktop_os_release',return_value={'ID':'fedora','VERSION_ID':'44'}):
            self.assertFalse(easy.inspect()['compatible'])

if __name__=='__main__':unittest.main()
