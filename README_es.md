<p align="center"><img src="assets/gitcat.png" width="128" alt="GitCat"></p>

<h1 align="center">GitCat</h1>

<p align="center">Un cliente Git de escritorio rápido para Windows y macOS que funciona con GitHub, GitLab, Gitee, Gitea, Bitbucket, Azure DevOps y cualquier otro host git.</p>

<p align="center"><a href="README.md">English</a> · <a href="README_zh.md">简体中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_fr.md">Français</a> · <b>Español</b> · <a href="README_pt.md">Português</a> · <a href="README_th.md">ไทย</a> · <a href="README_ms.md">Bahasa Melayu</a> · <a href="README_ru.md">Русский</a></p>

## Funciones

| Área | Qué incluye |
| --- | --- |
| Cambios | Listas preparado / sin preparar con filtro, **preparación por bloque y por línea**, diff unificado o **lado a lado** con resaltado de palabras, resolución de conflictos (nuestra / su versión / herramienta de fusión), amend, sign-off, confirmar y enviar |
| Historial | Gráfico de commits con insignias de ramas / etiquetas y avatares, filtro rápido, búsqueda profunda (mensaje / autor / código `-S` / ruta), comparar commits, blame, historial de archivo, restaurar cualquier versión |
| Archivos | Explorar el proyecto en el directorio de trabajo o en **cualquier rama, etiqueta o commit**, visor de código, búsqueda de contenido (`git grep`), **comparar cualquier versión de un archivo con otra** (también archivos fuera del repositorio) |
| Ramas y etiquetas | Cambiar, crear, renombrar, eliminar, upstream, fusión (ff / no-ff / ff-only / squash), rebase, **rebase interactivo**, cherry-pick, revert, reset, bisect, etiquetas (anotadas / ligeras, enviar / eliminar en remoto) |
| Publicación | **Publicación en un clic**: detecta archivos de versión, incrementa semver, actualiza `CHANGELOG.md`, confirma, etiqueta y envía, y muestra la CI que se lanzó |
| Cuentas | GitHub, GitLab, Gitee, Gitea / Forgejo, Bitbucket, Azure DevOps, cualquier host. Inicio de sesión con **token**, **navegador** (Git Credential Manager) o **SSH**; editar, verificar, predeterminar, cerrar sesión; vincular una cuenta a un repositorio |
| CI y versiones | GitHub Actions, pipelines de GitLab, Bitbucket Pipelines y Gitea Actions con estado de jobs / pasos; reejecutar, cancelar, lanzar; lista de versiones; crear pull / merge requests |
| Centro de comandos | **80 comandos git** como formularios con vista previa, enlace a la documentación y confirmación de operaciones peligrosas, además de una línea de comandos git libre |
| Más | Pestañas de repositorios, stashes, worktrees, submódulos, reflog, limpieza, parches, archivos, consola git, paleta de comandos (`Ctrl+Shift+P`), análisis, 4 temas, 10 idiomas, actualización automática |

## Cuentas y credenciales

GitCat usa el sistema de credenciales de git, así que lo que ya funciona en la línea de comandos funciona aquí:

1. **Configuración existente**: si `git push` funciona en una terminal (Git Credential Manager, Llavero, agente SSH, `~/.ssh/config`), GitCat usa las mismas credenciales sin configurar nada.
2. **Entorno**: se detectan `GITHUB_TOKEN`, `GH_TOKEN`, `GITLAB_TOKEN`, `GITEE_TOKEN`, `GITEA_TOKEN`, `BITBUCKET_TOKEN`, `AZURE_DEVOPS_EXT_PAT` y las CLI `gh` / `glab`, que se pueden importar en **Cuentas → Entorno**.
3. **Cuentas** (menú **Cuentas**, `Ctrl+Alt+A`):
   - **Token**: pega un token de acceso personal ("Crear token" abre la página correcta de cada proveedor); "Verificar" completa nombre, correo y avatar.
   - **Navegador**: inicia sesión con la ventana OAuth de Git Credential Manager (incluido en Git for Windows).
   - **SSH**: elige o genera una clave `ed25519`, copia la clave pública, abre la página de claves SSH del proveedor y prueba la conexión.
   - Los tokens se guardan en el almacén de credenciales del sistema con `git credential approve`. Guardarlos en la configuración de GitCat es posible, pero hay que elegirlo explícitamente.
4. **Varias cuentas en un mismo host**: "Usar en este repositorio" escribe `user.name`, `user.email`, `core.sshCommand` (SSH) o el usuario en la URL HTTPS, solo para ese repositorio.

GitLab / Gitea / GitHub Enterprise autoalojados funcionan escribiendo su nombre de host al añadir la cuenta.

## Instalación

Descarga el zip de tu plataforma desde [Releases](https://github.com/liu294100/git-cat/releases):

| Plataforma | Archivo |
| --- | --- |
| Windows 10/11 x64 | `GitCat-Windows-x64-onefile-v<versión>.zip` |
| macOS Apple Silicon | `GitCat-macOS-arm64-onefile-v<versión>.zip` |
| macOS Intel | `GitCat-macOS-x64-onefile-v<versión>.zip` |

Git debe estar instalado (Windows: [Git for Windows](https://git-scm.com/download/win); macOS: `xcode-select --install` o Homebrew). En macOS, la primera vez usa clic derecho → Abrir, porque la app no está notarizada.

Ayuda → *Buscar actualizaciones* descarga el zip nuevo, lo verifica con `SHA256SUMS`, reemplaza el programa y reinicia.

## Ejecutar desde el código fuente

```bash
python -m pip install -r requirements.txt
python -m gitcat [ruta/al/repositorio]
```

Se requiere Python 3.10 o superior.

## Compilación

| Plataforma | Comando | Resultado |
| --- | --- | --- |
| Windows | `release.bat [versión]` | `release/GitCat-Windows-x64-onefile-v<versión>.zip` |
| macOS | `./release.sh [versión]` | `release/GitCat-macOS-<arm64\|x64>-onefile-v<versión>.zip` |

Ambos scripts crean `.venv`, instalan `requirements-build.txt` y ejecutan PyInstaller con `GitCat.spec` (icono, información de versión de Windows, metadatos del bundle de macOS).

## Publicar una versión

1. Incrementa `__version__` en `gitcat/__init__.py` y añade una sección `## vX.Y.Z` a `CHANGELOG.md`.
2. Confirma y ejecuta `git tag vX.Y.Z && git push origin vX.Y.Z`, o usa el asistente 🚀 de GitCat.
3. `.github/workflows/release.yml` comprueba que la etiqueta coincide con `__version__`, compila Windows x64, macOS arm64 y macOS x64, genera `SHA256SUMS` y publica la GitHub Release con la sección del CHANGELOG como notas.

Ejecutar el workflow manualmente (`workflow_dispatch`) genera los paquetes como artefactos sin publicar.

## Arquitectura

```
gitcat/
├── core/        dominio git, sin Qt: modelos, ejecución de procesos, repositorio, diff/parches, gráfico,
│                análisis de URL de hosting, envoltorio de git credential
├── services/    casos de uso: instantáneas, cuentas, clientes REST de proveedores, catálogo de comandos,
│                publicación, actualización automática
├── common/      i18n, configuración, recursos, integración con el SO, utilidades de texto
├── ui/          PySide6: widgets, diálogos, páginas, vista de repositorio + mixins de operaciones, ventana principal, tema
└── locales/     traducciones <idioma>.json
```

Las dependencias solo van hacia abajo (`ui → services → core`; todos pueden usar `common`). Todo el trabajo git se ejecuta en un pool de hilos; al actualizar, las consultas de lectura van en paralelo y las peticiones se agrupan, el historial solo se recarga si cambia HEAD o una referencia, y `.git` se vigila en lugar de sondearse.

## Desarrollo

```bash
python -m pyflakes gitcat           # análisis estático
python scripts/check_locales.py     # todas las claves presentes en los 10 idiomas
python scripts/generate_icons.py    # regenerar assets/ (requiere Pillow)
```

Archivo de configuración: `%APPDATA%\GitCat\config.json` (Windows), `~/Library/Application Support/GitCat/config.json` (macOS).

El historial de versiones está en [CHANGELOG.md](CHANGELOG.md) (en inglés).
