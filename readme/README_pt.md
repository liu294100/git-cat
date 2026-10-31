<p align="center"><img src="../assets/gitcat.png" width="128" alt="GitCat"></p>

<h1 align="center">GitCat</h1>

<p align="center">Um cliente Git de desktop rápido para Windows e macOS que funciona com GitHub, GitLab, Gitee, Gitea, Bitbucket, Azure DevOps e qualquer outro host git.</p>

<p align="center"><a href="../README.md">English</a> · <a href="README_zh.md">简体中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_fr.md">Français</a> · <a href="README_es.md">Español</a> · <b>Português</b> · <a href="README_th.md">ไทย</a> · <a href="README_ms.md">Bahasa Melayu</a> · <a href="README_ru.md">Русский</a></p>

## Recursos

| Área | O que inclui |
| --- | --- |
| Alterações | Listas preparado / não preparado com filtro, **preparação por bloco e por linha**, diff unificado ou **lado a lado** com destaque de palavras, resolução de conflitos (nossa / deles / ferramenta de merge), amend, sign-off, commit e envio |
| Histórico | Gráfico de commits com selos de branches / tags e avatares, filtro rápido, pesquisa profunda (mensagem / autor / código `-S` / caminho), comparar commits, blame, histórico de arquivo, restaurar qualquer versão |
| Arquivos | Navegar pelo projeto na árvore de trabalho ou em **qualquer branch, tag ou commit**, visualizador de código, pesquisa de conteúdo (`git grep`), **comparar qualquer versão de um arquivo com outra** (inclusive arquivos fora do repositório) |
| Branches e tags | Checkout, criar, renomear, excluir, upstream, merge (ff / no-ff / ff-only / squash), rebase, **rebase interativo**, cherry-pick, revert, reset, bisect, tags (anotadas / leves, enviar / excluir no remoto) |
| Lançamento | **Lançamento em um clique**: detecta arquivos de versão, incrementa o semver, atualiza o `CHANGELOG.md`, faz commit, tag e push e mostra a CI disparada |
| Contas | GitHub, GitLab, Gitee, Gitea / Forgejo, Bitbucket, Azure DevOps, qualquer host. Login por **token**, **navegador** (Git Credential Manager) ou **SSH**; editar, verificar, tornar padrão, sair; vincular uma conta a um repositório |
| CI e releases | GitHub Actions, pipelines do GitLab, Bitbucket Pipelines e Gitea Actions com status de jobs / etapas; reexecutar, cancelar, disparar; lista de releases; criar pull / merge requests |
| Central de comandos | **80 comandos git** como formulários com prévia, link para a documentação e confirmação de operações perigosas, além de uma linha de comando git livre |
| Mais | Abas de repositórios, stashes, worktrees, submódulos, reflog, limpeza, patches, arquivos, console git, paleta de comandos (`Ctrl+Shift+P`), análise, 4 temas, 10 idiomas, atualização automática |

## Contas e credenciais

O GitCat usa o sistema de credenciais do próprio git; o que já funciona na linha de comando funciona aqui:

1. **Configuração existente**: se `git push` funciona no terminal (Git Credential Manager, Keychain, agente SSH, `~/.ssh/config`), o GitCat usa as mesmas credenciais sem configuração.
2. **Ambiente**: `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GITEE_TOKEN`, `GITEA_TOKEN`, `BITBUCKET_TOKEN`, `AZURE_DEVOPS_EXT_PAT` e as CLIs `gh` / `glab` são detectados e podem ser importados em **Contas → Ambiente**.
3. **Contas** (menu **Contas**, `Ctrl+Alt+A`):
   - **Token**: cole um token de acesso pessoal ("Criar token" abre a página certa de cada provedor); "Verificar" preenche nome, e-mail e avatar.
   - **Navegador**: login pela janela OAuth do Git Credential Manager (incluído no Git for Windows).
   - **SSH**: escolha ou gere uma chave `ed25519`, copie a chave pública, abra a página de chaves SSH do provedor e teste a conexão.
   - Os tokens ficam no armazenamento de credenciais do sistema via `git credential approve`. Guardá-los na configuração do GitCat é possível, mas precisa ser escolhido explicitamente.
4. **Várias contas no mesmo host**: "Usar neste repositório" grava `user.name`, `user.email`, `core.sshCommand` (SSH) ou o usuário na URL HTTPS, apenas nesse repositório.

GitLab / Gitea / GitHub Enterprise auto-hospedados funcionam informando o nome do host ao adicionar a conta.

## Instalação

Baixe o zip da sua plataforma em [Releases](https://github.com/liu294100/git-cat/releases):

| Plataforma | Arquivo |
| --- | --- |
| Windows 10/11 x64 | `GitCat-Windows-x64-onefile-v<versão>.zip` |
| macOS Apple Silicon | `GitCat-macOS-arm64-onefile-v<versão>.zip` |
| macOS Intel | `GitCat-macOS-x64-onefile-v<versão>.zip` |

O Git precisa estar instalado (Windows: [Git for Windows](https://git-scm.com/download/win); macOS: `xcode-select --install` ou Homebrew). No macOS, na primeira vez use clique direito → Abrir, pois o app não é notarizado.

Ajuda → *Verificar atualizações* baixa o novo zip, verifica com `SHA256SUMS`, substitui o programa e reinicia.

## Executar a partir do código

```bash
python -m pip install -r requirements.txt
python -m gitcat [caminho/do/repositório]
```

É necessário Python 3.10 ou superior.

## Compilação

| Plataforma | Comando | Resultado |
| --- | --- | --- |
| Windows | `release.bat [versão]` | `release/GitCat-Windows-x64-onefile-v<versão>.zip` |
| macOS | `./release.sh [versão]` | `release/GitCat-macOS-<arm64\|x64>-onefile-v<versão>.zip` |

Os dois scripts criam `.venv`, instalam `requirements-build.txt` e executam o PyInstaller com `GitCat.spec` (ícone, informações de versão do Windows, metadados do bundle macOS).

## Publicar uma versão

1. Incremente `__version__` em `gitcat/__init__.py` e adicione uma seção `## vX.Y.Z` ao `CHANGELOG.md`.
2. Faça commit e execute `git tag vX.Y.Z && git push origin vX.Y.Z`, ou use o assistente 🚀 do GitCat.
3. `.github/workflows/release.yml` verifica se a tag corresponde a `__version__`, compila Windows x64, macOS arm64 e macOS x64, gera `SHA256SUMS` e publica a GitHub Release com a seção do CHANGELOG como notas.

Executar o workflow manualmente (`workflow_dispatch`) gera os pacotes como artefatos sem publicar.

## Arquitetura

```
gitcat/
├── core/        domínio git, sem Qt: modelos, execução de processos, repositório, diff/patch, gráfico,
│                análise de URL de hospedagem, wrapper do git credential
├── services/    casos de uso: snapshots, contas, clientes REST dos provedores, catálogo de comandos,
│                lançamento, atualização automática
├── common/      i18n, configuração, recursos, integração com o SO, utilitários de texto
├── ui/          PySide6: widgets, diálogos, páginas, visão do repositório + mixins de operações, janela principal, tema
└── locales/     traduções <idioma>.json
```

As dependências apontam só para baixo (`ui → services → core`; todos podem usar `common`). Todo o trabalho git roda num pool de threads; ao atualizar, as consultas de leitura rodam em paralelo e os pedidos são agrupados, o histórico só recarrega quando HEAD ou uma referência muda, e o `.git` é monitorado em vez de consultado periodicamente.

## Desenvolvimento

```bash
python -m pyflakes gitcat           # análise estática
python scripts/check_locales.py     # todas as chaves presentes nos 10 idiomas
python scripts/generate_icons.py    # regenerar assets/ (requer Pillow)
```

Arquivo de configuração: `%APPDATA%\GitCat\config.json` (Windows), `~/Library/Application Support/GitCat/config.json` (macOS).

O histórico de versões está em [CHANGELOG.md](../CHANGELOG.md) (em inglês).
