# Git hooks — Xenty Acceso

Hooks versionados del repo. Se activan apuntando `core.hooksPath` a esta carpeta:

```bash
git config core.hooksPath .githooks
```

(Es config local por clon; córrela una vez tras clonar. `bootstrap.sh`/`.bat` no la aplican.)

## `pre-commit`

Antes de cada commit, formatea y lintea con **ruff** los archivos `.py` staged bajo `backend/`,
dentro del contenedor `backend` (no hay Python en el host), y los vuelve a agregar al commit.
Bloquea el commit si `ruff check` deja errores no auto-corregibles.

Así el paso "Ruff (lint + formato)" de CI (`.github/workflows/ci.yml`) no falla por formato.
Si el stack de Docker no está arriba, el hook avisa y **no** bloquea (permite commits offline);
en ese caso conviene correr manualmente antes de push:

```bash
docker compose exec backend sh -c "cd /app && ruff check . && ruff format --check ."
```
