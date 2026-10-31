<p align="center"><img src="assets/gitcat.png" width="128" alt="GitCat"></p>

<h1 align="center">GitCat</h1>

<p align="center">Klien Git desktop yang pantas untuk Windows dan macOS, berfungsi dengan GitHub, GitLab, Gitee, Gitea, Bitbucket, Azure DevOps dan mana-mana hos git lain.</p>

<p align="center"><a href="README.md">English</a> · <a href="README_zh.md">简体中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_fr.md">Français</a> · <a href="README_es.md">Español</a> · <a href="README_pt.md">Português</a> · <a href="README_th.md">ไทย</a> · <b>Bahasa Melayu</b> · <a href="README_ru.md">Русский</a></p>

## Ciri-ciri

| Bahagian | Kandungan |
| --- | --- |
| Perubahan | Senarai disediakan / belum disediakan dengan penapis, **penyediaan mengikut blok dan baris**, diff bersatu atau **sebelah-menyebelah** dengan sorotan perkataan, penyelesaian konflik (versi kita / mereka / alat gabung), amend, sign-off, komit dan tolak |
| Sejarah | Graf komit dengan lencana cabang / tag dan avatar, penapis pantas, carian mendalam (mesej / pengarang / kod `-S` / laluan), banding komit, blame, sejarah fail, pulihkan mana-mana versi fail |
| Fail | Layari projek pada pepohon kerja atau **mana-mana cabang, tag atau komit**, pemapar kod, carian kandungan (`git grep`), **banding mana-mana versi fail dengan versi lain** (termasuk fail di luar repositori) |
| Cabang & tag | Checkout, cipta, namakan semula, padam, upstream, gabung (ff / no-ff / ff-only / squash), rebase, **rebase interaktif**, cherry-pick, revert, reset, bisect, tag (beranotasi / ringan, tolak / padam jauh) |
| Keluaran | **Keluaran satu klik**: kesan fail versi, naikkan semver, kemas kini `CHANGELOG.md`, komit, tag dan tolak, kemudian paparkan CI yang dicetuskan |
| Akaun | GitHub, GitLab, Gitee, Gitea / Forgejo, Bitbucket, Azure DevOps, mana-mana hos. Log masuk dengan **token**, **pelayar** (Git Credential Manager) atau **SSH**; sunting, sahkan, jadikan lalai, log keluar; pautkan akaun ke repositori |
| CI & keluaran | Status kerja / langkah GitHub Actions, saluran GitLab, Bitbucket Pipelines dan Gitea Actions; jalankan semula, batal, cetuskan; senarai keluaran; cipta pull / merge request |
| Pusat Arahan | **80 arahan git** sebagai borang dengan pratonton, pautan dokumentasi dan pengesahan operasi berbahaya, serta baris arahan git bebas |
| Lain-lain | Tab berbilang repositori, stash, worktree, submodul, reflog, bersihkan, tampalan, arkib, konsol git, palet arahan (`Ctrl+Shift+P`), wawasan, 4 tema, 10 bahasa, kemas kini automatik |

## Akaun dan kelayakan

GitCat menggunakan sistem kelayakan git sendiri, jadi apa yang berfungsi di baris arahan juga berfungsi di sini:

1. **Persediaan sedia ada**: jika `git push` berfungsi dalam terminal (Git Credential Manager, Keychain, ejen SSH, `~/.ssh/config`), GitCat menggunakan kelayakan yang sama tanpa konfigurasi.
2. **Persekitaran**: `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GITEE_TOKEN`, `GITEA_TOKEN`, `BITBUCKET_TOKEN`, `AZURE_DEVOPS_EXT_PAT` serta CLI `gh` / `glab` dikesan dan boleh diimport di **Akaun → Persekitaran**.
3. **Akaun** (menu **Akaun**, `Ctrl+Alt+A`):
   - **Token**: tampal token akses peribadi ("Cipta token" membuka halaman yang betul bagi setiap penyedia); "Sahkan" mengisi nama, e-mel dan avatar.
   - **Pelayar**: log masuk melalui tetingkap OAuth Git Credential Manager (disertakan dengan Git for Windows).
   - **SSH**: pilih atau jana kunci `ed25519`, salin kunci awam, buka halaman kunci SSH penyedia dan uji sambungan.
   - Token disimpan dalam stor kelayakan sistem melalui `git credential approve`. Menyimpannya dalam konfigurasi GitCat boleh dilakukan tetapi mesti dipilih secara jelas.
4. **Beberapa akaun pada satu hos**: "Guna untuk repositori ini" menulis `user.name`, `user.email`, `core.sshCommand` (SSH) atau nama pengguna dalam URL HTTPS untuk repositori itu sahaja.

GitLab / Gitea / GitHub Enterprise yang dihoskan sendiri berfungsi dengan memasukkan nama hos semasa menambah akaun.

## Pemasangan

Muat turun zip untuk platform anda daripada [Releases](https://github.com/liu294100/git-cat/releases):

| Platform | Fail |
| --- | --- |
| Windows 10/11 x64 | `GitCat-Windows-x64-onefile-v<versi>.zip` |
| macOS Apple Silicon | `GitCat-macOS-arm64-onefile-v<versi>.zip` |
| macOS Intel | `GitCat-macOS-x64-onefile-v<versi>.zip` |

Git mesti dipasang (Windows: [Git for Windows](https://git-scm.com/download/win); macOS: `xcode-select --install` atau Homebrew). Pada macOS, kali pertama gunakan klik kanan → Buka kerana aplikasi belum dinotarikan.

Bantuan → *Semak kemas kini* memuat turun zip baharu, mengesahkannya dengan `SHA256SUMS`, menggantikan program dan memulakan semula.

## Jalankan daripada kod sumber

```bash
python -m pip install -r requirements.txt
python -m gitcat [laluan/repositori]
```

Python 3.10 atau lebih baharu diperlukan.

## Binaan

| Platform | Arahan | Hasil |
| --- | --- | --- |
| Windows | `release.bat [versi]` | `release/GitCat-Windows-x64-onefile-v<versi>.zip` |
| macOS | `./release.sh [versi]` | `release/GitCat-macOS-<arm64\|x64>-onefile-v<versi>.zip` |

Kedua-dua skrip mencipta `.venv`, memasang `requirements-build.txt` dan menjalankan PyInstaller dengan `GitCat.spec` (ikon, maklumat versi fail Windows, metadata bundle macOS).

## Menerbitkan keluaran

1. Naikkan `__version__` dalam `gitcat/__init__.py` dan tambah bahagian `## vX.Y.Z` dalam `CHANGELOG.md`.
2. Komit, kemudian `git tag vX.Y.Z && git push origin vX.Y.Z`, atau gunakan 🚀 keluaran satu klik GitCat.
3. `.github/workflows/release.yml` menyemak tag sepadan dengan `__version__`, membina Windows x64, macOS arm64 dan macOS x64, menulis `SHA256SUMS` dan menerbitkan GitHub Release dengan bahagian CHANGELOG sebagai nota.

Menjalankan aliran kerja secara manual (`workflow_dispatch`) membina pakej sebagai artifak tanpa menerbitkan.

## Seni bina

```
gitcat/
├── core/        domain git tanpa Qt: model, pelaksanaan proses, repositori, diff/tampalan, susun atur graf,
│                penghuraian URL hos, pembalut git credential
├── services/    kes guna: snapshot, akaun, klien REST penyedia, katalog arahan, keluaran, kemas kini automatik
├── common/      i18n, konfigurasi, sumber, integrasi OS, alat teks
├── ui/          PySide6: widget, dialog, halaman, paparan repositori + mixin operasi, tetingkap utama, tema
└── locales/     terjemahan <bahasa>.json
```

Kebergantungan hanya ke bawah (`ui → services → core`; semua boleh menggunakan `common`). Semua kerja git berjalan dalam kolam benang; muat semula menjalankan pertanyaan baca secara selari dan menggabungkan permintaan, sejarah hanya dimuat semula apabila HEAD atau ref berubah, dan `.git` dipantau dan bukannya ditinjau berulang kali.

## Pembangunan

```bash
python -m pyflakes gitcat           # semakan statik
python scripts/check_locales.py     # semua kunci wujud dalam 10 bahasa
python scripts/generate_icons.py    # jana semula assets/ (memerlukan Pillow)
```

Fail konfigurasi: `%APPDATA%\GitCat\config.json` (Windows), `~/Library/Application Support/GitCat/config.json` (macOS).

Sejarah keluaran ada dalam [CHANGELOG.md](CHANGELOG.md) (bahasa Inggeris).
