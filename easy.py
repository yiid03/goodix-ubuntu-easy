#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ubuntu GNOME installer UI/CLI. Never enrolls or exports biometric data."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import threading

from build_driver import build, VERSION

HERE = Path(__file__).resolve().parent
TEXT = {
 'en': {
  'title':'Goodix Fingerprint Setup','subtitle':'Ubuntu GNOME · Goodix 27c6:5125',
  'check':'Check compatibility','install':'Install / repair','settings':'Add fingerprints in Settings',
  'remove':'Remove driver','working':'Working… Please keep this window open.',
  'warning':'Experimental community driver. Tested on one MateBook D15 with Ubuntu 26.10. Occasional initialization errors remain. Password login stays available.',
  'privacy':'Fingerprint enrollment happens in Ubuntu Settings. This app does not read fingerprints or pairing keys.',
  'ready':'Compatible device found.','unsupported':'Unsupported configuration.',
  'installed':'Driver is active. Use Settings to enroll a finger.',
  'success':'Completed.','failed':'Action failed. See details below.',
  'confirm':'Remove the driver? Enrolled fingerprints and pairing data will be kept.',
  'cancel':'Cancel','yes':'Remove','status':'Status','details':'Details',
  'notice':'Installation builds bundled source locally. Ubuntu may ask for administrator authentication twice: dependencies, then activation.',
 },
 'tr': {
  'title':'Goodix Parmak İzi Kurulumu','subtitle':'Ubuntu GNOME · Goodix 27c6:5125',
  'check':'Uyumluluğu kontrol et','install':'Kur / onar','settings':'Ayarlar’dan parmak izi ekle',
  'remove':'Sürücüyü kaldır','working':'İşlem sürüyor… Lütfen pencereyi açık tut.',
  'warning':'Deneysel topluluk sürücüsü. Ubuntu 26.10 kullanan tek bir MateBook D15 üzerinde denendi. Ara sıra başlangıç hatası verebilir. Parolayla giriş korunur.',
  'privacy':'Parmak izi kaydı Ubuntu Ayarlar’da yapılır. Bu uygulama parmak izlerini veya eşleştirme anahtarlarını okumaz.',
  'ready':'Uyumlu okuyucu bulundu.','unsupported':'Bu yapılandırma desteklenmiyor.',
  'installed':'Sürücü etkin. Parmak eklemek için Ayarlar’ı aç.',
  'success':'İşlem tamamlandı.','failed':'İşlem başarısız. Ayrıntılar aşağıda.',
  'confirm':'Sürücü kaldırılsın mı? Kayıtlı parmak izleri ve eşleştirme verileri korunur.',
  'cancel':'Vazgeç','yes':'Kaldır','status':'Durum','details':'Ayrıntılar',
  'notice':'Kurulum, paket içindeki kaynakları bilgisayarında derler. Ubuntu iki kez yönetici doğrulaması isteyebilir: bağımlılıklar ve etkinleştirme için.',
 }
}

def inspect():
    release = platform.freedesktop_os_release()
    desktop = os.environ.get('XDG_CURRENT_DESKTOP','')
    usb = subprocess.run(['lsusb','-d','27c6:5125'],capture_output=True,text=True) if shutil.which('lsusb') else None
    gdm = Path('/etc/pam.d/gdm-fingerprint')
    reasons = []
    if (release.get('ID'),release.get('VERSION_ID'),platform.machine()) != ('ubuntu','26.10','x86_64'):
        reasons.append('Required: Ubuntu 26.10 x86-64.')
    if 'GNOME' not in desktop.upper() or not gdm.is_file() or 'pam_fprintd.so' not in gdm.read_text():
        reasons.append('Required: GNOME with GDM fingerprint authentication.')
    if usb is None or usb.returncode or '27c6:5125' not in usb.stdout:
        reasons.append('Required: USB device 27c6:5125 (usbutils must be installed).')
    result = subprocess.run(['systemctl','show','fprintd.service','-p','Environment','--value'],capture_output=True,text=True)
    enabled = 'LD_LIBRARY_PATH=/opt/goodix-5125-ubuntu/lib' in result.stdout
    return {'compatible': not reasons, 'reasons':reasons, 'active':enabled,
            'os': release.get('PRETTY_NAME','Unknown'),'desktop':desktop,'version':VERSION}

def privileged(action, *args):
    if os.geteuid() == 0:
        raise RuntimeError('Open the application as your normal user.')
    subprocess.run(['pkexec','/usr/bin/python3',str(HERE/'helper.py'),action,*map(str,args)],check=True)

def install():
    info = inspect()
    print(json.dumps(info,indent=2),flush=True)
    if not info['compatible']:
        raise RuntimeError('\n'.join(info['reasons']))
    privileged('dependencies')
    cache = Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'goodix-ubuntu-easy'
    cache.mkdir(mode=0o700,parents=True,exist_ok=True)
    # A private temporary build contains public source only, no USB captures.
    with tempfile.TemporaryDirectory(prefix='compile-',dir=cache) as temporary:
        built = build(HERE,Path(temporary)/'payload')
        privileged('activate',built)
    result = subprocess.run(['fprintd-list',str(__import__('getpass').getuser())],capture_output=True,text=True,
                            env=dict(os.environ, LC_ALL='C'))
    if result.returncode or 'Goodix 27c6:5125' not in result.stdout:
        raise RuntimeError('Installed, but fprintd did not enumerate the reader. Use Remove driver to restore the distribution library.')
    print(result.stdout,flush=True)
    print('DONE: open Ubuntu Settings → System → Users → Fingerprint Login.',flush=True)

def open_settings():
    # Current GNOME uses system/users; older versions use the users panel.
    subprocess.Popen(['gnome-control-center','system','users'])

def gui(language):
    if os.geteuid() == 0:
        raise RuntimeError('Open the application as your normal user, without sudo.')
    import gi
    gi.require_version('Gtk','4.0')
    from gi.repository import Gtk, GLib

    class Window(Gtk.ApplicationWindow):
        def __init__(self,app):
            super().__init__(application=app,title=TEXT[language]['title'],default_width=700,default_height=710)
            self.lang = language
            self.busy = False
            self.connect('close-request',lambda *_: self.busy)
            outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
            for name in ('top','bottom','start','end'): getattr(outer,'set_margin_'+name)(24)
            self.set_child(outer)
            self.title_label=Gtk.Label(xalign=0);self.title_label.add_css_class('title-1');outer.append(self.title_label)
            outer.append(Gtk.Label(label='Ubuntu GNOME · Goodix 27c6:5125',xalign=0))
            self.languages=Gtk.DropDown.new_from_strings(['Türkçe','English'])
            self.languages.set_selected(0 if language=='tr' else 1)
            self.languages.connect('notify::selected',self.translate);outer.append(self.languages)
            self.warning=Gtk.Label(wrap=True,xalign=0);outer.append(self.warning)
            self.state=Gtk.Label(wrap=True,xalign=0);self.state.add_css_class('heading');outer.append(self.state)
            self.buttons={}
            for action in ('check','install','settings','remove'):
                button=Gtk.Button();self.buttons[action]=button;outer.append(button)
                button.connect('clicked',lambda b,a=action:self.action(a))
            self.buttons['install'].add_css_class('suggested-action')
            self.buttons['remove'].add_css_class('destructive-action')
            self.notice=Gtk.Label(wrap=True,xalign=0);outer.append(self.notice)
            self.privacy=Gtk.Label(wrap=True,xalign=0);self.privacy.add_css_class('dim-label');outer.append(self.privacy)
            scroll=Gtk.ScrolledWindow(vexpand=True,min_content_height=140)
            self.log=Gtk.TextView(editable=False,monospace=True,wrap_mode=Gtk.WrapMode.WORD_CHAR)
            scroll.set_child(self.log);outer.append(scroll)
            self.translate()
            self.refresh()
        def translate(self,*_):
            self.lang='tr' if self.languages.get_selected()==0 else 'en'
            t=TEXT[self.lang];self.set_title(t['title']);self.title_label.set_text(t['title'])
            for key,label in self.buttons.items():label.set_label(t[key])
            self.warning.set_text(t['warning']);self.notice.set_text(t['notice']);self.privacy.set_text(t['privacy'])
            if not self.busy:self.refresh()
        def refresh(self):
            info=inspect();t=TEXT[self.lang]
            self.state.set_text(t['installed'] if info['active'] else (t['ready'] if info['compatible'] else t['unsupported']+'\n'+'\n'.join(info['reasons'])))
            self.buttons['install'].set_sensitive(info['compatible'])
            self.buttons['settings'].set_sensitive(info['active'])
        def append(self,line):
            buffer=self.log.get_buffer();buffer.insert(buffer.get_end_iter(),line)
            return False
        def finish(self,code):
            self.busy=False
            for button in self.buttons.values():button.set_sensitive(True)
            self.refresh()
            self.append('\n'+TEXT[self.lang]['success' if code==0 else 'failed']+'\n')
            return False
        def action(self,action):
            if self.busy:return
            if action=='check':
                self.append(json.dumps(inspect(),indent=2)+'\n');self.refresh();return
            if action=='settings':open_settings();return
            if action=='remove':
                dialog=Gtk.MessageDialog(transient_for=self,modal=True,text=TEXT[self.lang]['confirm'])
                dialog.add_button(TEXT[self.lang]['cancel'],Gtk.ResponseType.CANCEL)
                dialog.add_button(TEXT[self.lang]['yes'],Gtk.ResponseType.OK)
                def response(d,r):
                    d.destroy()
                    if r==Gtk.ResponseType.OK:self.start('remove')
                dialog.connect('response',response);dialog.present();return
            self.start('install')
        def start(self,action):
            self.busy=True;self.state.set_text(TEXT[self.lang]['working'])
            for button in self.buttons.values():button.set_sensitive(False)
            def worker():
                try:
                    process=subprocess.Popen(['/usr/bin/python3','-u',str(HERE/'easy.py'),action],
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                    for line in process.stdout:GLib.idle_add(self.append,line)
                    code=process.wait()
                except Exception as error:
                    GLib.idle_add(self.append,str(error)+'\n');code=1
                GLib.idle_add(self.finish,code)
            threading.Thread(target=worker,daemon=True).start()

    app=Gtk.Application(application_id='io.github.goodixubuntu.EasySetup')
    app.connect('activate',lambda a:Window(a).present())
    return app.run([])

def main():
    parser=argparse.ArgumentParser(description='Goodix 27c6:5125 installer for Ubuntu 26.10 GNOME')
    parser.add_argument('action',nargs='?',choices=['check','install','remove','settings'])
    parser.add_argument('--language',choices=['tr','en'],default='tr' if os.environ.get('LANG','').startswith('tr') else 'en')
    args=parser.parse_args()
    if args.action=='check':
        info=inspect();print(json.dumps(info,indent=2));return 0 if info['compatible'] else 2
    if args.action=='install':install()
    elif args.action=='remove':privileged('remove')
    elif args.action=='settings':open_settings()
    else:return gui(args.language)
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as error:
        print('ERROR:',error,file=sys.stderr);sys.exit(1)
