# Third-party source and attribution

This project distributes Ubuntu installer code, not an independently developed fingerprint driver.

The unmodified bundled source archive is produced by `git archive` from:

- Project: https://github.com/sorguido/goodix-27c6-5125
- Revision: `184e9aa1b47c4d6da19c7b95be85d0a7f55a95b2`
- Driver version: 3.0.0
- Archive: `vendor/goodix-source.tar.gz`
- Archive SHA-256: `5337c96f4b0c3a10be5bbb592e88077476e0c9d0a7857e370e86965f441b64ba`

Original copyright, SPDX notices, licenses, source inventories and provenance records remain inside the archive. The combined library is conveyed under GPL-3.0-or-later; constituent files retain their own terms. Installation builds this library locally; this project ships no precompiled fingerprint driver.

Relevant upstream contributions include libfprint, the Goodix protocol/driver project by Guido Sorarù and contributors, Rockytkg's GPL configuration/pairing work as identified in the upstream provenance ledger, and the ChicagoHS computational backend from berkekbgz/libfprint-goodix-spi at `010a665f54089a1632b1ab7be588b316ace934e2`. See the archive's `ACKNOWLEDGEMENTS.md`, `docs/LICENSING_AND_PROVENANCE.md`, `production/source-files.tsv`, and `production/chicago-native/{LICENSE,NOTICES.txt,PROVENANCE.md}` for exact attribution and per-file terms. This summary does not replace those original notices.

System dependencies such as GTK, PyGObject, OpenSSL, fprintd and Linux-PAM come from Ubuntu and are not bundled as binaries. Their respective licenses apply independently.

No OEM firmware or binary, protected key, private capture, fingerprint image or enrolled template is distributed by this installer.
