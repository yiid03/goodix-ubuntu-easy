# Goodix Ubuntu Easy

An experimental graphical installer for the **Goodix USB 27c6:5125** fingerprint reader on **Ubuntu 26.10 x86-64, GNOME/GDM**. English and Turkish interface.

This is Ubuntu installation tooling around [sorguido/goodix-27c6-5125](https://github.com/sorguido/goodix-27c6-5125), **not a new fingerprint driver**. Credit for the driver, reverse engineering and biometric engine belongs to the upstream projects. No affiliation with Huawei, Honor, Goodix or Canonical is implied.

[Türkçe açıklama](README.tr.md)

## What it does

- Checks Ubuntu version, desktop and the exact USB identifier before installation.
- Builds the pinned, bundled public source **as the ordinary user**. Administrative authentication is requested only for Ubuntu dependencies and final activation.
- Uses a private library directory instead of overwriting Ubuntu's libfprint packages.
- Keeps GNOME's dedicated fingerprint login path and avoids a second fingerprint request through the password authentication path. **sudo and general administrator prompts use passwords.**
- Opens **Settings → System → Users** for fingerprint enrollment. Enrollment is handled by GNOME/fprintd, not by this installer.
- Supports removal, preserving enrolled fingerprints and protected host pairing state.
- Has **no telemetry**, firmware flashing, fingerprint export or pairing-key export.

## Scope and limitations

**Experimental preview (0.1.0).** The driver was observed working on one Huawei MateBook D15 with an Intel i5-1135G7, Ubuntu 26.10 and Goodix 27c6:5125. Enrollment, direct verification, screen unlock and an immediate-touch wake test succeeded. Intermittent initialization failures also occurred. This is not a claim of universal reliability, security certification, broad false-accept testing or compatibility with every MateBook.

Other Ubuntu releases, architectures, desktops and USB IDs are intentionally refused. Upstream firmware allowlists are retained (APP12508/APP12509); **USB detection alone does not prove that the sensor's firmware is compatible**. The upstream driver checks its exact firmware and device profile before pairing. Installation itself does not open the sensor or flash firmware. First enrollment/verification may create a device-specific host pairing key through the upstream driver's normal bounded activation flow.

No fixed three-second delay is inserted. You can try touching the sensor as soon as the login screen appears. If initialization fails, lift your finger and retry, or use your password. New enrollment may need short touches separated by a few seconds. Fingerprint login may not unlock a password-encrypted GNOME keyring.

## Easy installation

Download the `.deb` from [GitHub Releases](https://github.com/yiid03/goodix-ubuntu-easy/releases). Version 0.1.0 is an experimental preview.

```bash
sudo apt install ./goodix-ubuntu-easy_0.1.0_amd64.deb
```

Open **Goodix Fingerprint Setup** from the application menu. Choose **Install / repair**, approve the Ubuntu administrator prompts, and wait for compilation to finish. Then choose **Add fingerprints in Settings**, unlock Users settings with your password if asked, and use **Fingerprint Login** to add a finger. The Settings button opens the Users page; it does not bypass GNOME's administrator prompt or automatically enroll a finger.

The `.deb` installs the setup application only. Driver activation happens when you choose Install. Installing the application does not change PAM or access the reader.

### From the source archive

Install `python3`, `python3-gi`, `gir1.2-gtk-4.0`, `pkexec`, `usbutils`, `fprintd`, `libpam-fprintd` and `gnome-control-center` from Ubuntu first. Then extract the archive and run:

```bash
sh install.sh
# Turkish interface:
sh install.sh --language tr
# Command-line alternatives:
sh install.sh check
sh install.sh install
sh install.sh settings
sh install.sh remove
```

Do **not** launch the application or compile the driver as root. The application requests elevation through Ubuntu's PolicyKit dialog. Download dependencies require network access; the pinned driver source is bundled, and compilation downloads no code. Official Ubuntu archive URLs are used over HTTPS where the standard `ubuntu.sources` file is available; system repository files are not edited.

## Remove or recover

Choose **Remove driver** in the application. It removes this installation's service override and library, restores the prior common-auth fingerprint preference, and preserves fingerprint templates and pairing data.

If the application is unavailable, use the installed standalone recovery helper:

```bash
sudo python3 /opt/goodix-5125-ubuntu/helper.py remove
```

**Remove the driver before removing the installer `.deb`.** Removing the application package alone leaves an activated driver in place. The standalone recovery helper remains available with the driver. Never delete `/var/lib/fprint/goodix-5125-state-v2/` as a troubleshooting shortcut: it contains private pairing state required to reopen the sensor.

The installer refuses partial, modified or unknown installations. Its own receipt-verified installation can be repaired/updated. One explicitly recognized manual predecessor is supported; unrelated forks or modified libraries require manual review. A software exception during activation triggers rollback. Abrupt power loss is not an atomic transaction across PAM, systemd and the filesystem: use the recovery helper if needed. Password access must remain available.

## Source and licensing

Installer code: **GPL-3.0-or-later**. The bundled upstream source retains its per-file licenses and notices; see [THIRD_PARTY.md](THIRD_PARTY.md) and `LICENSE`.

Pinned upstream revision: `184e9aa1b47c4d6da19c7b95be85d0a7f55a95b2` (driver version 3.0.0).

Bundled source archive SHA-256:

```text
5337c96f4b0c3a10be5bbb592e88077476e0c9d0a7857e370e86965f441b64ba
```

The archive is the corresponding public source, including original notices, from that revision. The program verifies its hash before extracting it. No firmware blobs, protected keys, enrolled templates, personal device captures or private diagnostics are included in the distribution.

## Development and verification

```bash
python3 -m unittest discover -s tests -v
python3 packaging/build_deb.py
```

Tests use temporary simulated host directories and mocked system commands. They cover compatibility rejection, archive/hash validation, activation failures, rollback, removal, preservation and foreign-installation refusal. They do not prove clean-machine installation or biometric accuracy. Compilation and fprintd ABI checks have also been exercised on the development Ubuntu machine. Public release should remain a prerelease until a fresh-machine installation/removal and GNOME Settings enrollment have been independently checked.

## Reporting problems

Report Ubuntu version, desktop, USB ID, installer version and the short error message. Never post pairing directories, keys, raw fingerprint images, enrolled templates or complete unredacted device-debug logs. Do not weaken matching thresholds to solve a recognition failure.
