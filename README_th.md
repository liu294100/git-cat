<p align="center"><img src="assets/gitcat.png" width="128" alt="GitCat"></p>

<h1 align="center">GitCat</h1>

<p align="center">ไคลเอนต์ Git บนเดสก์ท็อปที่รวดเร็วสำหรับ Windows และ macOS รองรับ GitHub, GitLab, Gitee, Gitea, Bitbucket, Azure DevOps และโฮสต์ git อื่นๆ ทั้งหมด</p>

<p align="center"><a href="README.md">English</a> · <a href="README_zh.md">简体中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_fr.md">Français</a> · <a href="README_es.md">Español</a> · <a href="README_pt.md">Português</a> · <b>ไทย</b> · <a href="README_ms.md">Bahasa Melayu</a> · <a href="README_ru.md">Русский</a></p>

## ความสามารถ

| หมวด | รายละเอียด |
| --- | --- |
| การเปลี่ยนแปลง | รายการเตรียมแล้ว / ยังไม่เตรียมพร้อมตัวกรอง **เตรียมทีละส่วนและทีละบรรทัด** diff แบบรวมหรือ**แสดงคู่กัน**พร้อมไฮไลต์คำ แก้ข้อขัดแย้ง (ของเรา / ของเขา / เครื่องมือรวม) amend, sign-off, คอมมิตแล้วพุช |
| ประวัติ | กราฟคอมมิตพร้อมป้ายสาขา / แท็กและอวาตาร์ ตัวกรองด่วน ค้นหาเชิงลึก (ข้อความ / ผู้เขียน / โค้ด `-S` / พาธ) เปรียบเทียบคอมมิต blame ประวัติไฟล์ กู้คืนไฟล์ทุกเวอร์ชัน |
| ไฟล์ | เรียกดูโปรเจกต์ที่พื้นที่ทำงานหรือ**สาขา แท็ก คอมมิตใดก็ได้** ตัวดูโค้ด ค้นหาเนื้อหา (`git grep`) **เปรียบเทียบไฟล์เวอร์ชันใดก็ได้กับอีกเวอร์ชัน** (รวมถึงไฟล์นอกรีโพ) |
| สาขาและแท็ก | เช็กเอาต์ สร้าง เปลี่ยนชื่อ ลบ upstream รวม (ff / no-ff / ff-only / squash) รีเบส **รีเบสแบบโต้ตอบ** เชอร์รีพิก ย้อนกลับ รีเซ็ต bisect แท็ก (มีคำอธิบาย / แบบเบา พุช / ลบบนรีโมต) |
| รีลีส | **รีลีสในคลิกเดียว**: ตรวจหาไฟล์เวอร์ชัน เพิ่ม semver อัปเดต `CHANGELOG.md` คอมมิต ติดแท็ก พุช แล้วแสดง CI ที่ถูกเรียก |
| บัญชี | GitHub, GitLab, Gitee, Gitea / Forgejo, Bitbucket, Azure DevOps และโฮสต์ใดก็ได้ เข้าสู่ระบบด้วย**โทเค็น** **เบราว์เซอร์** (Git Credential Manager) หรือ **SSH** แก้ไข ตรวจสอบ ตั้งค่าเริ่มต้น ออกจากระบบ ผูกบัญชีกับรีโพ |
| CI และรีลีส | สถานะงาน / ขั้นตอนของ GitHub Actions, GitLab pipelines, Bitbucket Pipelines และ Gitea Actions รันใหม่ ยกเลิก สั่งรัน รายการรีลีส สร้าง pull / merge request |
| ศูนย์คำสั่ง | **80 คำสั่ง git** ในรูปแบบฟอร์ม พร้อมพรีวิวบรรทัดคำสั่ง ลิงก์เอกสาร และการยืนยันคำสั่งอันตราย รวมถึงช่องพิมพ์คำสั่ง git อิสระ |
| อื่นๆ | แท็บหลายรีโพ สแตช เวิร์กทรี ซับโมดูล reflog ล้างไฟล์ แพตช์ ไฟล์เก็บถาวร คอนโซล git ชุดคำสั่ง (`Ctrl+Shift+P`) ข้อมูลเชิงลึก 4 ธีม 10 ภาษา อัปเดตอัตโนมัติ |

## บัญชีและข้อมูลรับรอง

GitCat ใช้ระบบข้อมูลรับรองของ git เอง สิ่งที่ใช้ได้ในบรรทัดคำสั่งจึงใช้ได้ที่นี่เช่นกัน:

1. **การตั้งค่าเดิม**: ถ้า `git push` ใช้งานได้ในเทอร์มินัล (Git Credential Manager, Keychain, SSH agent, `~/.ssh/config`) GitCat จะใช้ข้อมูลรับรองเดียวกันโดยไม่ต้องตั้งค่า
2. **สภาพแวดล้อม**: ตรวจพบ `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GITEE_TOKEN`, `GITEA_TOKEN`, `BITBUCKET_TOKEN`, `AZURE_DEVOPS_EXT_PAT` และ CLI `gh` / `glab` และนำเข้าได้ที่ **บัญชี → สภาพแวดล้อม**
3. **บัญชี** (เมนู **บัญชี**, `Ctrl+Alt+A`):
   - **โทเค็น**: วางโทเค็นส่วนบุคคล ("สร้างโทเค็น" จะเปิดหน้าที่ถูกต้องของแต่ละผู้ให้บริการ) กด "ตรวจสอบ" เพื่อเติมชื่อ อีเมล และอวาตาร์
   - **เบราว์เซอร์**: เข้าสู่ระบบผ่านหน้าต่าง OAuth ของ Git Credential Manager (มากับ Git for Windows)
   - **SSH**: เลือกหรือสร้างคีย์ `ed25519` คัดลอกคีย์สาธารณะ เปิดหน้าคีย์ SSH ของผู้ให้บริการ และทดสอบการเชื่อมต่อ
   - โทเค็นถูกเก็บในที่เก็บข้อมูลรับรองของระบบผ่าน `git credential approve` การเก็บในไฟล์ตั้งค่าของ GitCat ทำได้แต่ต้องเลือกเอง
4. **หลายบัญชีบนโฮสต์เดียว**: "ใช้กับรีโพนี้" จะเขียน `user.name`, `user.email`, `core.sshCommand` (SSH) หรือชื่อผู้ใช้ใน URL HTTPS เฉพาะรีโพนั้น

GitLab / Gitea / GitHub Enterprise ที่โฮสต์เองใช้ได้โดยกรอกชื่อโฮสต์ตอนเพิ่มบัญชี

## การติดตั้ง

ดาวน์โหลด zip ของแพลตฟอร์มคุณจาก [Releases](https://github.com/liu294100/git-cat/releases):

| แพลตฟอร์ม | ไฟล์ |
| --- | --- |
| Windows 10/11 x64 | `GitCat-Windows-x64-onefile-v<version>.zip` |
| macOS Apple Silicon | `GitCat-macOS-arm64-onefile-v<version>.zip` |
| macOS Intel | `GitCat-macOS-x64-onefile-v<version>.zip` |

ต้องติดตั้ง Git ก่อน (Windows: [Git for Windows](https://git-scm.com/download/win); macOS: `xcode-select --install` หรือ Homebrew) บน macOS ครั้งแรกให้คลิกขวา → เปิด เพราะแอปยังไม่ได้ผ่าน notarization

ช่วยเหลือ → *ตรวจหาอัปเดต* จะดาวน์โหลด zip ใหม่ ตรวจสอบด้วย `SHA256SUMS` แทนที่โปรแกรม และรีสตาร์ต

## รันจากซอร์สโค้ด

```bash
python -m pip install -r requirements.txt
python -m gitcat [พาธรีโพ]
```

ต้องใช้ Python 3.10 ขึ้นไป

## การสร้างแพ็กเกจ

| แพลตฟอร์ม | คำสั่ง | ผลลัพธ์ |
| --- | --- | --- |
| Windows | `release.bat [version]` | `release/GitCat-Windows-x64-onefile-v<version>.zip` |
| macOS | `./release.sh [version]` | `release/GitCat-macOS-<arm64\|x64>-onefile-v<version>.zip` |

ทั้งสองสคริปต์สร้าง `.venv` ติดตั้ง `requirements-build.txt` และรัน PyInstaller ด้วย `GitCat.spec` (ไอคอน ข้อมูลเวอร์ชันไฟล์ Windows และข้อมูล bundle ของ macOS)

## การเผยแพร่รีลีส

1. เพิ่ม `__version__` ใน `gitcat/__init__.py` และเพิ่มหัวข้อ `## vX.Y.Z` ใน `CHANGELOG.md`
2. คอมมิต แล้วรัน `git tag vX.Y.Z && git push origin vX.Y.Z` หรือใช้ 🚀 รีลีสในคลิกเดียวของ GitCat
3. `.github/workflows/release.yml` ตรวจว่าแท็กตรงกับ `__version__` สร้าง Windows x64, macOS arm64 และ macOS x64 สร้าง `SHA256SUMS` และเผยแพร่ GitHub Release โดยใช้หัวข้อใน CHANGELOG เป็นบันทึก

การรันเวิร์กโฟลว์ด้วยตนเอง (`workflow_dispatch`) จะสร้างแพ็กเกจเป็น artifact โดยไม่เผยแพร่

## สถาปัตยกรรม

```
gitcat/
├── core/        โดเมน git ไม่มี Qt: โมเดล การรันโปรเซส รีโพ diff/แพตช์ เลย์เอาต์กราฟ
│                การแยก URL ของโฮสต์ ตัวห่อ git credential
├── services/    use case: สแนปช็อต บัญชี ไคลเอนต์ REST ของผู้ให้บริการ แค็ตตาล็อกคำสั่ง รีลีส อัปเดตอัตโนมัติ
├── common/      หลายภาษา การตั้งค่า ทรัพยากร การเชื่อมกับระบบปฏิบัติการ เครื่องมือข้อความ
├── ui/          PySide6: วิดเจ็ต ไดอะล็อก หน้า มุมมองรีโพ + mixin การทำงาน หน้าต่างหลัก ธีม
└── locales/     คำแปล <ภาษา>.json
```

การพึ่งพาชี้ลงล่างเท่านั้น (`ui → services → core` ทุกชั้นใช้ `common` ได้) งาน git ทั้งหมดรันใน thread pool การรีเฟรชรันคำสั่งอ่านแบบขนานและรวมคำขอซ้ำ ประวัติจะโหลดใหม่เมื่อ HEAD หรือ ref เปลี่ยนเท่านั้น และเฝ้าดู `.git` แทนการวนตรวจ

## การพัฒนา

```bash
python -m pyflakes gitcat           # ตรวจโค้ด
python scripts/check_locales.py     # ตรวจว่าทุกคีย์มีครบ 10 ภาษา
python scripts/generate_icons.py    # สร้าง assets/ ใหม่ (ต้องใช้ Pillow)
```

ไฟล์ตั้งค่า: `%APPDATA%\GitCat\config.json` (Windows), `~/Library/Application Support/GitCat/config.json` (macOS)

ดูประวัติเวอร์ชันได้ที่ [CHANGELOG.md](CHANGELOG.md) (ภาษาอังกฤษ)
