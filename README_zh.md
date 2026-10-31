<p align="center"><img src="assets/gitcat.png" width="128" alt="GitCat"></p>

<h1 align="center">GitCat</h1>

<p align="center">适用于 Windows 和 macOS 的高性能 Git 桌面客户端，支持 GitHub、GitLab、Gitee、Gitea、Bitbucket、Azure DevOps 以及任意 git 托管平台。</p>

<p align="center"><a href="README.md">English</a> · <b>简体中文</b> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_fr.md">Français</a> · <a href="README_es.md">Español</a> · <a href="README_pt.md">Português</a> · <a href="README_th.md">ไทย</a> · <a href="README_ms.md">Bahasa Melayu</a> · <a href="README_ru.md">Русский</a></p>

## 功能

| 模块 | 内容 |
| --- | --- |
| 变更 | 已暂存 / 未暂存列表与筛选，**按块、按行暂存**，统一或**并排**差异视图（含行内高亮），冲突处理（我方 / 对方 / 合并工具），修改提交、Sign-off、提交并推送 |
| 历史 | 泳道提交图、分支 / 标签徽章与头像，快速筛选，深度搜索（信息 / 作者 / 代码 `-S` / 路径），提交比较，逐行追溯，文件历史，恢复任意文件版本 |
| 文件 | 在工作区或**任意分支、标签、提交**下浏览项目，代码查看器，全文搜索（`git grep`），**任意文件版本互相比较**（也可比较仓库外的文件） |
| 分支与标签 | 检出、新建、重命名、删除、上游设置，合并（快进 / no-ff / 仅快进 / squash），变基，**交互式变基**，拣选，还原，重置，二分查找，标签（附注 / 轻量，推送 / 删除远程） |
| 发版 | **一键发版**：识别版本文件、递增语义化版本、更新 `CHANGELOG.md`、提交、打标签并推送，随后显示被触发的 CI |
| 账号 | GitHub、GitLab、Gitee、Gitea / Forgejo、Bitbucket、Azure DevOps 及任意主机。支持**令牌**、**浏览器**（Git Credential Manager）、**SSH** 登录；编辑、验证、设为默认、退出；把账号绑定到仓库 |
| CI 与发布 | GitHub Actions、GitLab 流水线、Bitbucket Pipelines、Gitea Actions 的任务 / 步骤状态；重跑、取消、手动触发；发布列表；创建 PR / MR |
| 命令中心 | **80 个 git 命令**以表单形式呈现，实时预览命令行、文档链接、危险操作确认，另有自由输入的 git 命令行 |
| 其他 | 多仓库标签页、贮藏、工作树、子模块、reflog、清理、补丁、归档、git 控制台、命令面板（`Ctrl+Shift+P`）、仓库洞察、4 套主题、10 种语言、自动更新 |

## 账号与凭据

GitCat 直接使用 git 自身的凭据体系，命令行里能用的方式在这里同样可用：

1. **现有环境**：只要终端里 `git push` 正常（Git Credential Manager、钥匙串、SSH agent、`~/.ssh/config`），GitCat 无需任何配置即可使用同样的凭据。
2. **环境变量**：`GITHUB_TOKEN`、`GH_TOKEN`、`GITLAB_TOKEN`、`GITEE_TOKEN`、`GITEA_TOKEN`、`BITBUCKET_TOKEN`、`AZURE_DEVOPS_EXT_PAT` 以及 `gh` / `glab` 命令行都会被自动识别，可在 **账号 → 环境** 中导入。
3. **账号**（菜单 **账号**，`Ctrl+Alt+A`）：
   - **令牌**：粘贴个人访问令牌（“创建令牌”会打开对应平台的页面），点“验证”自动填入姓名、邮箱和头像。
   - **浏览器**：通过 Git Credential Manager 的 OAuth 窗口登录（Git for Windows 自带）。
   - **SSH**：选择或生成 `ed25519` 密钥，复制公钥，打开平台的 SSH 密钥页面，测试连接。
   - 令牌通过 `git credential approve` 保存在系统凭据库中；如需保存到 GitCat 配置文件，必须手动选择。
4. **同一主机多个账号**：“用于当前仓库”只对该仓库写入 `user.name`、`user.email`、`core.sshCommand`（SSH）或 HTTPS 远程 URL 中的用户名。

自建的 GitLab / Gitea / GitHub Enterprise 只需在添加账号时填写自己的主机名。

## 安装

在 [Releases](https://github.com/liu294100/git-cat/releases) 下载对应平台的 zip：

| 平台 | 文件 |
| --- | --- |
| Windows 10/11 x64 | `GitCat-Windows-x64-onefile-v<版本>.zip` |
| macOS Apple 芯片 | `GitCat-macOS-arm64-onefile-v<版本>.zip` |
| macOS Intel | `GitCat-macOS-x64-onefile-v<版本>.zip` |

需要先安装 Git（Windows：[Git for Windows](https://git-scm.com/download/win)；macOS：`xcode-select --install` 或 Homebrew）。macOS 首次打开请右键 → 打开（应用未经公证）。

帮助 → *检查更新* 会下载新版 zip，按 `SHA256SUMS` 校验后替换程序并重启。

## 从源码运行

```bash
python -m pip install -r requirements.txt
python -m gitcat [仓库路径]
```

需要 Python 3.10 及以上。

## 打包

| 平台 | 命令 | 产物 |
| --- | --- | --- |
| Windows | `release.bat [版本]` | `release/GitCat-Windows-x64-onefile-v<版本>.zip` |
| macOS | `./release.sh [版本]` | `release/GitCat-macOS-<arm64\|x64>-onefile-v<版本>.zip` |

两个脚本都会创建 `.venv`、安装 `requirements-build.txt`，并用 `GitCat.spec` 调用 PyInstaller（含图标、Windows 文件版本信息、macOS 应用包信息）。

## 发布新版本

1. 修改 `gitcat/__init__.py` 中的 `__version__`，并在 `CHANGELOG.md` 中添加 `## vX.Y.Z` 小节。
2. 提交后执行 `git tag vX.Y.Z && git push origin vX.Y.Z`，或直接使用 GitCat 的 🚀 一键发版。
3. `.github/workflows/release.yml` 会校验标签与 `__version__` 一致，构建 Windows x64、macOS arm64、macOS x64，生成 `SHA256SUMS`，并以 CHANGELOG 对应小节作为说明发布 GitHub Release。

手动运行该工作流（`workflow_dispatch`）只构建产物，不发布。

## 架构

```
gitcat/
├── core/        git 领域层，无 Qt：模型、进程执行、仓库门面、差异/补丁、提交图布局、
│                托管平台 URL 解析、git 凭据封装
├── services/    用例层：快照加载、账号、平台 REST 客户端、命令目录、发版、自动更新
├── common/      国际化、配置、资源、系统集成、文本工具
├── ui/          PySide6：控件、对话框、页面、仓库视图与操作 mixin、主窗口、主题
└── locales/     <语言>.json 翻译
```

依赖只向下（`ui → services → core`，都可使用 `common`）。所有 git 操作都在线程池中执行；刷新时只读查询并行执行且会合并重复请求，只有 HEAD 或引用变化时才重新加载历史，`.git` 目录采用文件监听而非轮询。

## 开发

```bash
python -m pyflakes gitcat           # 代码检查
python scripts/check_locales.py     # 检查 10 种语言的翻译是否齐全
python scripts/generate_icons.py    # 重新生成 assets/（需要 Pillow）
```

配置文件：`%APPDATA%\GitCat\config.json`（Windows）、`~/Library/Application Support/GitCat/config.json`（macOS）。

更新记录见 [CHANGELOG.md](CHANGELOG.md)（英文）。
