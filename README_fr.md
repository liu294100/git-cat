<p align="center"><img src="assets/gitcat.png" width="128" alt="GitCat"></p>

<h1 align="center">GitCat</h1>

<p align="center">Un client Git de bureau rapide pour Windows et macOS, compatible avec GitHub, GitLab, Gitee, Gitea, Bitbucket, Azure DevOps et tout autre hébergeur git.</p>

<p align="center"><a href="README.md">English</a> · <a href="README_zh.md">简体中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <b>Français</b> · <a href="README_es.md">Español</a> · <a href="README_pt.md">Português</a> · <a href="README_th.md">ไทย</a> · <a href="README_ms.md">Bahasa Melayu</a> · <a href="README_ru.md">Русский</a></p>

## Fonctionnalités

| Domaine | Contenu |
| --- | --- |
| Modifications | Listes indexé / non indexé avec filtre, **indexation par bloc et par ligne**, diff unifié ou **côte à côte** avec surlignage des mots, résolution de conflits (notre / leur version / outil de fusion), amend, sign-off, valider et pousser |
| Historique | Graphe des commits avec badges de branches / tags et avatars, filtre rapide, recherche approfondie (message / auteur / code `-S` / chemin), comparaison de commits, blame, historique de fichier, restauration de n'importe quelle version |
| Fichiers | Parcourir le projet dans l'arbre de travail ou à **n'importe quelle branche, tag ou commit**, visionneuse de code, recherche dans le contenu (`git grep`), **comparer n'importe quelle version d'un fichier avec une autre** (y compris un fichier hors du dépôt) |
| Branches et tags | Extraire, créer, renommer, supprimer, amont, fusion (ff / no-ff / ff-only / squash), rebase, **rebase interactif**, cherry-pick, revert, reset, bisect, tags (annotés / légers, pousser / supprimer à distance) |
| Publication | **Publication en un clic** : détecte les fichiers de version, incrémente le semver, met à jour `CHANGELOG.md`, valide, tague et pousse, puis affiche la CI déclenchée |
| Comptes | GitHub, GitLab, Gitee, Gitea / Forgejo, Bitbucket, Azure DevOps, tout hôte. Connexion par **jeton**, **navigateur** (Git Credential Manager) ou **SSH** ; modifier, vérifier, définir par défaut, se déconnecter ; associer un compte à un dépôt |
| CI et versions | GitHub Actions, pipelines GitLab, Bitbucket Pipelines et Gitea Actions avec l'état des jobs / étapes ; relancer, annuler, déclencher ; liste des versions ; créer des pull / merge requests |
| Centre de commandes | **80 commandes git** sous forme de formulaires avec aperçu, lien vers la documentation et confirmation des opérations dangereuses, plus une ligne de commande git libre |
| Et aussi | Onglets multi-dépôts, remises, arbres de travail, sous-modules, reflog, nettoyage, patchs, archives, console git, palette de commandes (`Ctrl+Shift+P`), statistiques, 4 thèmes, 10 langues, mise à jour automatique |

## Comptes et identifiants

GitCat utilise le système d'identifiants de git ; ce qui fonctionne en ligne de commande fonctionne aussi ici :

1. **Configuration existante** : si `git push` fonctionne dans un terminal (Git Credential Manager, Trousseau, agent SSH, `~/.ssh/config`), GitCat utilise les mêmes identifiants sans configuration.
2. **Environnement** : `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GITEE_TOKEN`, `GITEA_TOKEN`, `BITBUCKET_TOKEN`, `AZURE_DEVOPS_EXT_PAT` ainsi que les CLI `gh` / `glab` sont détectés et importables via **Comptes → Environnement**.
3. **Comptes** (menu **Comptes**, `Ctrl+Alt+A`) :
   - **Jeton** : collez un jeton d'accès personnel (« Créer un jeton » ouvre la bonne page chez chaque fournisseur) ; « Vérifier » remplit nom, e-mail et avatar.
   - **Navigateur** : connexion via la fenêtre OAuth de Git Credential Manager (inclus dans Git for Windows).
   - **SSH** : choisissez ou générez une clé `ed25519`, copiez la clé publique, ouvrez la page des clés SSH du fournisseur, testez la connexion.
   - Les jetons sont enregistrés dans le magasin d'identifiants du système via `git credential approve`. Le stockage dans la configuration de GitCat doit être choisi explicitement.
4. **Plusieurs comptes sur un même hôte** : « Utiliser pour ce dépôt » écrit `user.name`, `user.email`, `core.sshCommand` (SSH) ou le nom d'utilisateur dans l'URL HTTPS, pour ce dépôt uniquement.

Les instances auto-hébergées GitLab / Gitea / GitHub Enterprise fonctionnent en saisissant leur nom d'hôte lors de l'ajout du compte.

## Installation

Téléchargez le zip de votre plateforme depuis [Releases](https://github.com/liu294100/git-cat/releases) :

| Plateforme | Fichier |
| --- | --- |
| Windows 10/11 x64 | `GitCat-Windows-x64-onefile-v<version>.zip` |
| macOS Apple Silicon | `GitCat-macOS-arm64-onefile-v<version>.zip` |
| macOS Intel | `GitCat-macOS-x64-onefile-v<version>.zip` |

Git doit être installé (Windows : [Git for Windows](https://git-scm.com/download/win) ; macOS : `xcode-select --install` ou Homebrew). Sur macOS, faites clic droit → Ouvrir au premier lancement, car l'application n'est pas notariée.

Aide → *Rechercher des mises à jour* télécharge le nouveau zip, le vérifie avec `SHA256SUMS`, remplace le programme et redémarre.

## Exécuter depuis les sources

```bash
python -m pip install -r requirements.txt
python -m gitcat [chemin/du/dépôt]
```

Python 3.10 ou plus récent est requis.

## Compilation

| Plateforme | Commande | Résultat |
| --- | --- | --- |
| Windows | `release.bat [version]` | `release/GitCat-Windows-x64-onefile-v<version>.zip` |
| macOS | `./release.sh [version]` | `release/GitCat-macOS-<arm64\|x64>-onefile-v<version>.zip` |

Les deux scripts créent `.venv`, installent `requirements-build.txt` et lancent PyInstaller avec `GitCat.spec` (icône, informations de version Windows, métadonnées du bundle macOS).

## Publier une version

1. Incrémentez `__version__` dans `gitcat/__init__.py` et ajoutez une section `## vX.Y.Z` à `CHANGELOG.md`.
2. Validez, puis `git tag vX.Y.Z && git push origin vX.Y.Z`, ou utilisez l'assistant 🚀 de GitCat.
3. `.github/workflows/release.yml` vérifie que le tag correspond à `__version__`, compile Windows x64, macOS arm64 et macOS x64, génère `SHA256SUMS` et publie la GitHub Release avec la section du CHANGELOG comme notes.

Lancer le workflow manuellement (`workflow_dispatch`) produit les paquets en artefacts sans publier.

## Architecture

```
gitcat/
├── core/        domaine git, sans Qt : modèles, exécution des processus, dépôt, diff/patch, graphe,
│                analyse des URL d'hébergeur, enveloppe git credential
├── services/    cas d'usage : instantanés, comptes, clients REST des fournisseurs, catalogue de commandes,
│                publication, mise à jour automatique
├── common/      i18n, configuration, ressources, intégration OS, utilitaires texte
├── ui/          PySide6 : widgets, dialogues, pages, vue dépôt + mixins d'opérations, fenêtre principale, thème
└── locales/     traductions <langue>.json
```

Les dépendances vont uniquement vers le bas (`ui → services → core`, tous peuvent utiliser `common`). Tout le travail git s'exécute dans un pool de threads ; l'actualisation lance ses requêtes en parallèle et regroupe les demandes, l'historique n'est rechargé que si HEAD ou une référence change, et `.git` est surveillé plutôt qu'interrogé en boucle.

## Développement

```bash
python -m pyflakes gitcat           # analyse statique
python scripts/check_locales.py     # toutes les clés présentes dans les 10 langues
python scripts/generate_icons.py    # régénérer assets/ (nécessite Pillow)
```

Fichier de configuration : `%APPDATA%\GitCat\config.json` (Windows), `~/Library/Application Support/GitCat/config.json` (macOS).

L'historique des versions se trouve dans [CHANGELOG.md](CHANGELOG.md) (en anglais).
