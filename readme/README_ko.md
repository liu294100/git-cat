<p align="center"><img src="../assets/gitcat.png" width="128" alt="GitCat"></p>

<h1 align="center">GitCat</h1>

<p align="center">Windows와 macOS용 빠른 Git 데스크톱 클라이언트. GitHub, GitLab, Gitee, Gitea, Bitbucket, Azure DevOps 및 모든 git 호스트를 지원합니다.</p>

<p align="center"><a href="../README.md">English</a> · <a href="README_zh.md">简体中文</a> · <a href="README_ja.md">日本語</a> · <b>한국어</b> · <a href="README_fr.md">Français</a> · <a href="README_es.md">Español</a> · <a href="README_pt.md">Português</a> · <a href="README_th.md">ไทย</a> · <a href="README_ms.md">Bahasa Melayu</a> · <a href="README_ru.md">Русский</a></p>

## 기능

| 영역 | 내용 |
| --- | --- |
| 변경 | 스테이징됨 / 안 됨 목록과 필터, **헝크·줄 단위 스테이징**, 통합 또는 **나란히 보기** diff(단어 강조), 충돌 해결(내 버전 / 상대 버전 / 병합 도구), amend, sign-off, 커밋 후 푸시 |
| 기록 | 레인 커밋 그래프, 브랜치 / 태그 배지와 아바타, 빠른 필터, 심층 검색(메시지 / 작성자 / 코드 `-S` / 경로), 커밋 비교, blame, 파일 기록, 모든 파일 버전 복원 |
| 파일 | 작업 트리 또는 **모든 브랜치·태그·커밋** 기준으로 프로젝트 탐색, 코드 뷰어, 내용 검색(`git grep`), **어떤 파일 버전이든 서로 비교**(저장소 밖 파일 포함) |
| 브랜치와 태그 | 체크아웃, 생성, 이름 변경, 삭제, 업스트림, 병합(ff / no-ff / ff-only / squash), 리베이스, **대화형 리베이스**, 체리픽, 되돌리기, 리셋, bisect, 태그(주석 / 경량, 원격 푸시 / 삭제) |
| 릴리스 | **원클릭 릴리스**: 버전 파일을 찾아 semver를 올리고 `CHANGELOG.md` 갱신, 커밋·태그·푸시 후 실행된 CI 표시 |
| 계정 | GitHub, GitLab, Gitee, Gitea / Forgejo, Bitbucket, Azure DevOps, 모든 호스트. **토큰**, **브라우저**(Git Credential Manager), **SSH** 로그인; 편집, 확인, 기본 설정, 로그아웃, 저장소에 계정 연결 |
| CI와 릴리스 | GitHub Actions, GitLab 파이프라인, Bitbucket Pipelines, Gitea Actions의 작업 / 단계 상태; 재실행, 취소, 수동 실행; 릴리스 목록; PR / MR 생성 |
| 명령 센터 | **80개 git 명령**을 양식으로 제공, 명령줄 미리보기, 문서 링크, 위험 작업 확인, 자유 입력 git 명령줄 |
| 기타 | 여러 저장소 탭, 스태시, 워크트리, 서브모듈, reflog, clean, 패치, 아카이브, git 콘솔, 명령 팔레트(`Ctrl+Shift+P`), 인사이트, 테마 4개, 언어 10개, 자동 업데이트 |

## 계정과 자격 증명

GitCat은 git 자체의 자격 증명 시스템을 사용하므로 명령줄에서 쓰던 방식이 그대로 작동합니다.

1. **기존 환경**: 터미널에서 `git push`가 된다면(Git Credential Manager, 키체인, SSH 에이전트, `~/.ssh/config`) 별도 설정 없이 같은 자격 증명을 사용합니다.
2. **환경 변수**: `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GITEE_TOKEN`, `GITEA_TOKEN`, `BITBUCKET_TOKEN`, `AZURE_DEVOPS_EXT_PAT`와 `gh` / `glab` CLI를 감지하며 **계정 → 환경**에서 가져올 수 있습니다.
3. **계정**(메뉴 **계정**, `Ctrl+Alt+A`):
   - **토큰**: 개인 액세스 토큰을 붙여 넣고("토큰 만들기"가 각 서비스의 페이지를 엶) "확인"을 누르면 이름, 이메일, 아바타가 채워집니다.
   - **브라우저**: Git Credential Manager의 OAuth 창으로 로그인(Git for Windows에 포함).
   - **SSH**: `ed25519` 키를 선택하거나 생성하고, 공개 키 복사, 서비스의 SSH 키 페이지 열기, 연결 테스트.
   - 토큰은 `git credential approve`로 시스템 자격 증명 저장소에 저장됩니다. GitCat 설정 파일에 저장하려면 직접 선택해야 합니다.
4. **한 호스트에 여러 계정**: "이 저장소에 사용"은 해당 저장소에만 `user.name`, `user.email`, `core.sshCommand`(SSH) 또는 HTTPS 원격 URL의 사용자 이름을 기록합니다.

자체 호스팅 GitLab / Gitea / GitHub Enterprise는 계정을 추가할 때 호스트 이름만 입력하면 됩니다.

## 설치

[Releases](https://github.com/liu294100/git-cat/releases)에서 플랫폼에 맞는 zip을 내려받으세요.

| 플랫폼 | 파일 |
| --- | --- |
| Windows 10/11 x64 | `GitCat-Windows-x64-onefile-v<version>.zip` |
| macOS Apple Silicon | `GitCat-macOS-arm64-onefile-v<version>.zip` |
| macOS Intel | `GitCat-macOS-x64-onefile-v<version>.zip` |

Git이 설치되어 있어야 합니다(Windows: [Git for Windows](https://git-scm.com/download/win), macOS: `xcode-select --install` 또는 Homebrew). macOS에서는 공증되지 않은 앱이므로 처음에는 우클릭 → 열기를 선택하세요.

도움말 → *업데이트 확인*은 새 zip을 내려받아 `SHA256SUMS`로 검증한 뒤 프로그램을 교체하고 다시 시작합니다.

## 소스에서 실행

```bash
python -m pip install -r requirements.txt
python -m gitcat [저장소 경로]
```

Python 3.10 이상이 필요합니다.

## 빌드

| 플랫폼 | 명령 | 결과 |
| --- | --- | --- |
| Windows | `release.bat [version]` | `release/GitCat-Windows-x64-onefile-v<version>.zip` |
| macOS | `./release.sh [version]` | `release/GitCat-macOS-<arm64\|x64>-onefile-v<version>.zip` |

두 스크립트 모두 `.venv`를 만들고 `requirements-build.txt`를 설치한 뒤 `GitCat.spec`으로 PyInstaller를 실행합니다(아이콘, Windows 파일 버전 정보, macOS 번들 정보 포함).

## 릴리스 게시

1. `gitcat/__init__.py`의 `__version__`을 올리고 `CHANGELOG.md`에 `## vX.Y.Z` 섹션을 추가합니다.
2. 커밋 후 `git tag vX.Y.Z && git push origin vX.Y.Z`를 실행하거나 GitCat의 🚀 원클릭 릴리스를 사용합니다.
3. `.github/workflows/release.yml`이 태그와 `__version__`의 일치를 확인하고 Windows x64, macOS arm64, macOS x64를 빌드한 뒤 `SHA256SUMS`를 만들고 CHANGELOG 섹션을 본문으로 GitHub Release를 게시합니다.

워크플로를 수동 실행(`workflow_dispatch`)하면 게시하지 않고 패키지만 빌드합니다.

## 아키텍처

```
gitcat/
├── core/        git 도메인(Qt 없음): 모델, 프로세스 실행, 저장소, diff/패치, 그래프 레이아웃,
│                호스트 URL 파싱, git 자격 증명 래퍼
├── services/    유스케이스: 스냅샷, 계정, 서비스별 REST 클라이언트, 명령 카탈로그, 릴리스, 자동 업데이트
├── common/      다국어, 설정, 리소스, OS 연동, 텍스트 도구
├── ui/          PySide6: 위젯, 대화상자, 페이지, 저장소 뷰와 작업 mixin, 메인 창, 테마
└── locales/     <언어>.json 번역
```

의존성은 아래 방향으로만 흐릅니다(`ui → services → core`, 모두 `common` 사용 가능). 모든 git 작업은 스레드 풀에서 실행됩니다. 새로 고침 시 읽기 쿼리는 병렬로 실행되고 중복 요청은 합쳐지며, 기록은 HEAD나 참조가 바뀔 때만 다시 불러오고, `.git`은 폴링 대신 감시합니다.

## 개발

```bash
python -m pyflakes gitcat           # 정적 검사
python scripts/check_locales.py     # 10개 언어 번역 키 확인
python scripts/generate_icons.py    # assets/ 재생성(Pillow 필요)
```

설정 파일: `%APPDATA%\GitCat\config.json`(Windows), `~/Library/Application Support/GitCat/config.json`(macOS).

변경 기록은 [CHANGELOG.md](../CHANGELOG.md)(영어)를 참고하세요.
