# Goodix Ubuntu Easy

**Ubuntu 26.10, GNOME/GDM ve Goodix 27c6:5125** için deneysel kolay kurulum uygulaması. Türkçe ve İngilizce arayüz sunar.

Bu proje yeni bir parmak izi sürücüsü yazmaz; [sorguido/goodix-27c6-5125](https://github.com/sorguido/goodix-27c6-5125) sürücüsünün Ubuntu kurulumu için arayüz sağlar. Sürücü, tersine mühendislik ve parmak izi tanıma motoru için asıl emek ilgili açık kaynak projelere aittir. Huawei, Honor, Goodix veya Canonical ile bağlantılı değildir.

## Kurulum

[GitHub Releases](https://github.com/yiid03/goodix-ubuntu-easy/releases) bölümünden `.deb` paketini indir. 0.1.0 paketi deneysel önizlemedir.

```bash
sudo apt install ./goodix-ubuntu-easy_0.1.0_amd64.deb
```

Uygulama menüsünden **Goodix Parmak İzi Kurulumu** uygulamasını aç. **Kur / onar** düğmesine bas, Ubuntu'nun yönetici pencerelerini onayla ve derleme bitene kadar bekle. **Ayarlar’dan parmak izi ekle** düğmesiyle Kullanıcılar sayfasına git. Gerekirse parolanla ayar kilidini açıp **Parmak İziyle Giriş** bölümünden parmağını ekle.

Türkçe arayüzü ayrıca şöyle açabilirsin:

```bash
goodix-ubuntu-easy --language tr
```

`.deb` yalnızca kurulum uygulamasını ekler. Sürücü, uygulamadaki Kur düğmesine bastığında etkinleştirilir. Derleme normal kullanıcıyla yapılır; bağımlılıklar ve etkinleştirme için yönetici onayı istenir. Kaynak kod paket içinde sabit sürüm olarak bulunur. Sistem paketleri için internet gerekir.

## Neleri korur?

Ubuntu'nun libfprint dosyalarının üzerine yazmaz; sürücüyü ayrı bir dizine kurar. Okuyucuya firmware yüklemez. GNOME'un kendi parmak izi yolunu kullanır; çift erişim oluşmaması için ortak parola yolundaki parmak izi denemesini kapatır. **sudo ve genel yönetici onayları parola kullanır.** Parmak izi kaydı Ubuntu Ayarlar/fprintd tarafından yapılır. Uygulama parmak izlerini, eşleştirme anahtarlarını veya kişisel cihaz kayıtlarını dışarı aktarmaz.

## Bilinen sınırlar

Yalnızca bir Huawei MateBook D15 i5-1135G7 ve Ubuntu 26.10 üzerinde sürücü denenmiştir. Kayıt, doğrulama, ekran kilidi ve beklemeden uyanış denemesi başarılı oldu; ara sıra başlangıç ölçümü hataları da görüldü. Her cihazda veya her denemede başarı garantisi yoktur. Yeni kurulum uygulaması için testler simüle edilmiş sistem klasörlerinde çalışır; temiz bir bilgisayarda uçtan uca kurulum ve Ayarlar’dan kayıt henüz bağımsız doğrulanmadı.

Farklı Ubuntu sürümleri, masaüstleri, mimariler ve USB kimlikleri kurulumda reddedilir. USB kimliğinin eşleşmesi firmware uyumluluğu garantisi değildir; kesin firmware ve cihaz kontrolü sürücüde ilk gerçek işlem sırasında yapılır. İlk kayıt/doğrulamada sürücü bilgisayara özel eşleştirme anahtarı oluşturabilir.

Sabit 3 saniye bekleme eklenmez. Ekran görünür görünmez okutmayı deneyebilirsin. Başlangıç hatası olursa parmağını kaldırıp kısa süre sonra tekrar dene veya parolanla giriş yap. Yeni parmak kaydında kısa dokunuşların arasında birkaç saniye beklemek gerekebilir. Parmak iziyle giriş, parola ile şifrelenmiş GNOME anahtarlığını otomatik açmayabilir.

## Kaldırma

Uygulamada **Sürücüyü kaldır** düğmesini kullan. Kayıtlı parmak izleri ve eşleştirme verileri korunur. Önceki genel parmak izi kimlik doğrulama tercihi geri yüklenir.

Uygulama açılmıyorsa terminalde:

```bash
sudo python3 /opt/goodix-5125-ubuntu/helper.py remove
```

**Uygulama paketini silmeden önce sürücüyü kaldır.** Sadece `.deb` uygulamasını kaldırmak sürücüyü devreden çıkarmaz; kurtarma yardımcısı sürücü dizininde kalır. `/var/lib/fprint/goodix-5125-state-v2/` dizinini silme veya paylaşma.

Yarım kalmış, değiştirilmiş veya başka bir projeye ait kurulum varsa uygulama üzerine yazmadan durur. Yazılımsal etkinleştirme hatalarında geri alma yapılır; elektrik kesintisi gibi kesintiler için tüm sistemi kapsayan atomik işlem garantisi yoktur. Parolanı kullanılabilir tut.

## Kaynak paketinden çalıştırma

Önce Ubuntu'dan `python3`, `python3-gi`, `gir1.2-gtk-4.0`, `pkexec`, `usbutils`, `fprintd`, `libpam-fprintd`, `gnome-control-center` paketlerini kur. Arşivi açtıktan sonra:

```bash
sh install.sh --language tr
```

Komut satırı seçenekleri: `sh install.sh check`, `sh install.sh install`, `sh install.sh settings`, `sh install.sh remove`. Uygulamayı `sudo` ile başlatma; gerektiğinde kendi yönetici penceresini açar.

Lisans: kurulum araçları GPL-3.0-or-later. Asıl sürücünün lisansları ve katkıları [THIRD_PARTY.md](THIRD_PARTY.md) dosyasında açıklanır. Ayrıntılı teknik kapsam ve testler için [İngilizce açıklamaya](README.md) bak.
