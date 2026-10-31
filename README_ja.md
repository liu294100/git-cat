<p align="center"><img src="assets/gitcat.png" width="128" alt="GitCat"></p>

<h1 align="center">GitCat</h1>

<p align="center">Windows と macOS 向けの高速な Git デスクトップクライアント。GitHub、GitLab、Gitee、Gitea、Bitbucket、Azure DevOps など、あらゆる git ホストに対応します。</p>

<p align="center"><a href="README.md">English</a> · <a href="README_zh.md">简体中文</a> · <b>日本語</b> · <a href="README_ko.md">한국어</a> · <a href="README_fr.md">Français</a> · <a href="README_es.md">Español</a> · <a href="README_pt.md">Português</a> · <a href="README_th.md">ไทย</a> · <a href="README_ms.md">Bahasa Melayu</a> · <a href="README_ru.md">Русский</a></p>

## 機能

| 分類 | 内容 |
| --- | --- |
| 変更 | ステージ済み / 未ステージの一覧とフィルター、**ハンク単位・行単位のステージ**、統合 / **左右並び**の差分表示（単語ハイライト付き）、競合解決（自分 / 相手 / マージツール）、amend、sign-off、コミットしてプッシュ |
| 履歴 | レーン付きコミットグラフ、ブランチ / タグのバッジとアバター、クイックフィルター、詳細検索（メッセージ / 作成者 / コード `-S` / パス）、コミット比較、blame、ファイル履歴、任意バージョンの復元 |
| ファイル | 作業ツリーまたは**任意のブランチ・タグ・コミット**でプロジェクトを閲覧、コードビューアー、内容検索（`git grep`）、**任意のファイルバージョン同士を比較**（リポジトリ外のファイルも可） |
| ブランチとタグ | チェックアウト、作成、名前変更、削除、上流設定、マージ（ff / no-ff / ff-only / squash）、リベース、**対話的リベース**、チェリーピック、リバート、リセット、bisect、タグ（注釈付き / 軽量、リモートへのプッシュ / 削除） |
| リリース | **ワンクリックリリース**：バージョンファイルを検出し、semver を上げ、`CHANGELOG.md` を更新、コミット・タグ付け・プッシュし、起動された CI を表示 |
| アカウント | GitHub、GitLab、Gitee、Gitea / Forgejo、Bitbucket、Azure DevOps、任意のホスト。**トークン**・**ブラウザー**（Git Credential Manager）・**SSH** でサインイン。編集、確認、既定設定、サインアウト、リポジトリへの関連付け |
| CI とリリース | GitHub Actions、GitLab パイプライン、Bitbucket Pipelines、Gitea Actions のジョブ / ステップ状態。再実行、キャンセル、手動起動、リリース一覧、PR / MR の作成 |
| コマンドセンター | **80 個の git コマンド**をフォーム化。コマンドラインのプレビュー、ドキュメントへのリンク、危険な操作の確認、自由入力の git コマンドライン |
| その他 | 複数リポジトリのタブ、スタッシュ、ワークツリー、サブモジュール、reflog、clean、パッチ、アーカイブ、git コンソール、コマンドパレット（`Ctrl+Shift+P`）、分析、4 テーマ、10 言語、自動アップデート |

## アカウントと資格情報

GitCat は git 自身の資格情報の仕組みを使うため、コマンドラインで使っている方法がそのまま使えます。

1. **既存の環境**：ターミナルで `git push` ができていれば（Git Credential Manager、キーチェーン、SSH エージェント、`~/.ssh/config`）、設定なしで同じ資格情報を使います。
2. **環境変数**：`GITHUB_TOKEN`、`GH_TOKEN`、`GITLAB_TOKEN`、`GITEE_TOKEN`、`GITEA_TOKEN`、`BITBUCKET_TOKEN`、`AZURE_DEVOPS_EXT_PAT` と `gh` / `glab` CLI を検出し、**アカウント → 環境** からインポートできます。
3. **アカウント**（メニュー **アカウント**、`Ctrl+Alt+A`）：
   - **トークン**：個人アクセストークンを貼り付け（「トークンを作成」で各サービスのページを開く）、「確認」で名前・メール・アバターを取得。
   - **ブラウザー**：Git Credential Manager の OAuth 画面でサインイン（Git for Windows に同梱）。
   - **SSH**：`ed25519` 鍵を選択または生成し、公開鍵をコピー、サービスの SSH キーページを開き、接続をテスト。
   - トークンは `git credential approve` でシステムの資格情報ストアに保存されます。GitCat の設定ファイルへの保存は明示的に選んだ場合のみです。
4. **同じホストで複数アカウント**：「このリポジトリで使用」で、そのリポジトリだけに `user.name`、`user.email`、`core.sshCommand`（SSH）または HTTPS リモート URL のユーザー名を書き込みます。

セルフホストの GitLab / Gitea / GitHub Enterprise は、アカウント追加時にホスト名を入力するだけで使えます。

## インストール

[Releases](https://github.com/liu294100/git-cat/releases) からお使いの環境の zip をダウンロードします。

| 環境 | ファイル |
| --- | --- |
| Windows 10/11 x64 | `GitCat-Windows-x64-onefile-v<version>.zip` |
| macOS Apple シリコン | `GitCat-macOS-arm64-onefile-v<version>.zip` |
| macOS Intel | `GitCat-macOS-x64-onefile-v<version>.zip` |

Git が必要です（Windows：[Git for Windows](https://git-scm.com/download/win)、macOS：`xcode-select --install` または Homebrew）。macOS では公証されていないため、初回は右クリック → 開く を選んでください。

ヘルプ →「アップデートを確認」で新しい zip をダウンロードし、`SHA256SUMS` で検証して置き換え、再起動します。

## ソースから実行

```bash
python -m pip install -r requirements.txt
python -m gitcat [リポジトリのパス]
```

Python 3.10 以上が必要です。

## ビルド

| 環境 | コマンド | 出力 |
| --- | --- | --- |
| Windows | `release.bat [version]` | `release/GitCat-Windows-x64-onefile-v<version>.zip` |
| macOS | `./release.sh [version]` | `release/GitCat-macOS-<arm64\|x64>-onefile-v<version>.zip` |

どちらも `.venv` を作成して `requirements-build.txt` をインストールし、`GitCat.spec` で PyInstaller を実行します（アイコン、Windows のファイルバージョン情報、macOS バンドル情報を含む）。

## リリースの公開

1. `gitcat/__init__.py` の `__version__` を上げ、`CHANGELOG.md` に `## vX.Y.Z` セクションを追加します。
2. コミット後 `git tag vX.Y.Z && git push origin vX.Y.Z`、または GitCat の 🚀 ワンクリックリリースを使います。
3. `.github/workflows/release.yml` がタグと `__version__` の一致を確認し、Windows x64・macOS arm64・macOS x64 をビルド、`SHA256SUMS` を作成し、CHANGELOG の該当セクションを本文として GitHub Release を公開します。

ワークフローを手動実行（`workflow_dispatch`）すると、公開せずにパッケージだけをビルドします。

## アーキテクチャ

```
gitcat/
├── core/        git ドメイン層（Qt なし）：モデル、プロセス実行、リポジトリ、差分 / パッチ、グラフレイアウト、
│                ホスト URL 解析、git 資格情報ラッパー
├── services/    ユースケース：スナップショット、アカウント、各サービスの REST クライアント、コマンドカタログ、
│                リリース、自動アップデート
├── common/      多言語、設定、リソース、OS 連携、テキスト処理
├── ui/          PySide6：ウィジェット、ダイアログ、ページ、リポジトリビューと操作 mixin、メインウィンドウ、テーマ
└── locales/     <言語>.json 翻訳
```

依存は下向きのみ（`ui → services → core`、すべて `common` を利用可）。git の処理はすべてスレッドプールで実行。更新時の読み取りクエリは並列実行され、重複要求はまとめられます。履歴は HEAD か参照が変わったときだけ再読み込みし、`.git` はポーリングではなく監視します。

## 開発

```bash
python -m pyflakes gitcat           # 静的チェック
python scripts/check_locales.py     # 10 言語すべての翻訳キーを確認
python scripts/generate_icons.py    # assets/ を再生成（Pillow が必要）
```

設定ファイル：`%APPDATA%\GitCat\config.json`（Windows）、`~/Library/Application Support/GitCat/config.json`（macOS）。

変更履歴は [CHANGELOG.md](CHANGELOG.md)（英語）を参照してください。
