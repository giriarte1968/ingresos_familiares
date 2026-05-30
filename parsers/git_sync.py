import os
import subprocess
import logging
import json

logger = logging.getLogger(__name__)

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE = "origin"
BRANCH = "main"
STATE_BRANCH = os.environ.get("GIT_STATE_BRANCH", "do-state")

def _get_token():
    token = os.environ.get("GIT_WRITE_TOKEN", "")
    if not token:
        return ""
    return token

def _configure_git():
    try:
        subprocess.run(["git", "config", "user.name", "DO-Agent"],
                       cwd=REPO_DIR, capture_output=True)
        subprocess.run(["git", "config", "user.email", "do-agent@valu.app"],
                       cwd=REPO_DIR, capture_output=True)
    except Exception as e:
        logger.warning(f"[GIT_SYNC] Error configurando git: {e}")

def _ensure_branch():
    """Si estamos en detached HEAD, crear y switchear a branch main."""
    r = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"],
                       cwd=REPO_DIR, capture_output=True)
    if r.returncode != 0:
        logger.info("[GIT_SYNC] Detached HEAD detectado, creando branch main")
        subprocess.run(["git", "checkout", "-b", "main"],
                       cwd=REPO_DIR, capture_output=True)

def _auth_url():
    token = _get_token()
    if not token:
        return None
    return f"https://giriarte1968:{token}@github.com/giriarte1968/ingresos_familiares.git"


def _working_tree_clean() -> bool:
    """True si no hay cambios sin commit en el working tree."""
    r = subprocess.run(["git", "diff", "--quiet"],
                       cwd=REPO_DIR, capture_output=True)
    if r.returncode != 0:
        return False
    r2 = subprocess.run(["git", "diff", "--cached", "--quiet"],
                        cwd=REPO_DIR, capture_output=True)
    return r2.returncode == 0


def try_pull():
    """
    Sincroniza SOLO propiedades.json con el estado remoto de GitHub.
    Usa fetch + checkout selectivo para NO tocar valuaciones_cache.json
    (que es generado localmente y se perdería con un reset --hard).
    Solo actúa si el working tree está limpio (no descarta cambios locales).
    Retorna True si OK. Requiere token para repos privados.
    """
    _configure_git()
    _ensure_branch()
    url = _auth_url()
    if not url:
        logger.warning("[GIT_SYNC] try_pull: sin token, salteando")
        return False
    if not _working_tree_clean():
        logger.warning("[GIT_SYNC] try_pull: working tree sucio, salteando")
        return False
    try:
        fetch = subprocess.run(
            ["git", "fetch", url, BRANCH],
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=30
        )
        if fetch.returncode != 0:
            logger.warning(f"[GIT_SYNC] git fetch fallo: {fetch.stderr[:200]}")
            return False

        checkout = subprocess.run(
            ["git", "checkout", "FETCH_HEAD", "--", "propiedades.json"],
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=30
        )
        if checkout.returncode != 0:
            logger.warning(f"[GIT_SYNC] git checkout propiedades.json fallo: {checkout.stderr[:200]}")
            return False

        logger.info("[GIT_SYNC] propiedades.json sincronizado con FETCH_HEAD")
        return True
    except Exception as e:
        logger.warning(f"[GIT_SYNC] Error en pull: {e}")
        return False


def _check_unpushed() -> bool:
    """True si hay commits locales sin pushear."""
    r = subprocess.run(
        ["git", "rev-list", "--count", "HEAD", "--not", "--remotes=origin"],
        cwd=REPO_DIR, capture_output=True, text=True
    )
    return r.returncode == 0 and r.stdout.strip() not in ("", "0")

def _has_staged_changes() -> bool:
    r = subprocess.run(["git", "diff", "--cached", "--quiet"],
                       cwd=REPO_DIR)
    return r.returncode != 0

def try_sync(file_paths, commit_message="DO: actualizacion automatica de propiedades"):
    token = _get_token()
    if not token:
        return False

    _configure_git()
    _ensure_branch()
    url = _auth_url()
    if not url:
        return False

    try:
        add_result = subprocess.run(
            ["git", "add"] + file_paths,
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=30
        )
        if add_result.returncode != 0:
            logger.error(f"[GIT_SYNC] git add fallo: {add_result.stderr[:200]}")
            return False

        if not _has_staged_changes() and not _check_unpushed():
            return True

        if not _check_unpushed():
            r = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=REPO_DIR, capture_output=True, text=True,
                timeout=30
            )
            if r.returncode != 0:
                logger.error(f"[GIT_SYNC] git commit fallo: {r.stderr[:200]}")
                return False
            logger.info(f"[GIT_SYNC] Commit: {r.stdout[:100]}")

        push_result = subprocess.run(
            ["git", "push", url, f"HEAD:{BRANCH}"],
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=60
        )
        if push_result.returncode != 0:
            logger.error(f"[GIT_SYNC] git push fallo: {push_result.stderr[:200]}")
            return False

        logger.info("[GIT_SYNC] Push exitoso a GitHub")
        return True
    except subprocess.TimeoutExpired:
        logger.error("[GIT_SYNC] Timeout en operacion git")
        return False
    except Exception as e:
        logger.error(f"[GIT_SYNC] Error inesperado: {e}")
        return False


def try_sync_state(file_paths, commit_message="DO-STATE: sync runtime state"):
    """
    Sincroniza archivos de estado runtime a branch do-state.
    Nunca pushea a main. No dispara deploy si DO solo observa main.
    Retorna True si OK, False si falla o no hay token.
    """
    token = _get_token()
    if not token:
        logger.warning("[GIT_SYNC_STATE] sin token, salteando")
        return False

    _configure_git()
    _ensure_branch()
    url = _auth_url()
    if not url:
        return False

    branch = STATE_BRANCH

    try:
        add_result = subprocess.run(
            ["git", "add"] + file_paths,
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=30
        )
        if add_result.returncode != 0:
            logger.warning(f"[GIT_SYNC_STATE] git add fallo: {add_result.stderr[:200]}")
            return False

        # Si no hay cambios staged, no hay nada que pushear
        r_diff = subprocess.run(["git", "diff", "--cached", "--quiet"],
                                cwd=REPO_DIR, capture_output=True)
        if r_diff.returncode == 0:
            return True

        # Commit
        r_commit = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=30
        )
        if r_commit.returncode != 0:
            logger.warning(f"[GIT_SYNC_STATE] commit fallo: {r_commit.stderr[:200]}")
            return False

        # Push a do-state (NUNCA a main)
        push_result = subprocess.run(
            ["git", "push", url, f"HEAD:{branch}"],
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=60
        )
        if push_result.returncode != 0:
            logger.warning(f"[GIT_SYNC_STATE] push a {branch} fallo: {push_result.stderr[:200]}")
            return False

        logger.info(f"[GIT_SYNC_STATE] Push exitoso a origin/{branch}")
        return True

    except subprocess.TimeoutExpired:
        logger.warning("[GIT_SYNC_STATE] Timeout")
        return False
    except Exception as e:
        logger.warning(f"[GIT_SYNC_STATE] Error: {e}")
        return False
