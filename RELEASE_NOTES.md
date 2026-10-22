# 0.1.0 — experimental preview

Ubuntu 26.10 GNOME installer for Goodix 27c6:5125. English/Turkish GTK interface, pinned bundled source build, private driver activation, GNOME Users shortcut and receipt-checked removal/recovery.

The upstream driver has been observed working on one MateBook D15; intermittent initialization failures remain. The new installer has simulated transaction/rollback coverage and local compilation/ABI validation. Fresh-machine installation/removal and enrollment through GNOME Settings are still pending independent verification. Publish as a **prerelease**, not a broadly supported stable driver release.

Release assets: installer `.deb`, complete source archive and SHA-256 checksums. The `.deb` contains a setup application; driver activation is a separate explicit action inside the application. Keep upstream source, attribution and original license notices with every distribution.
