import os
import subprocess
import logging
import json

logger = logging.getLogger(__name__)

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE = "origin"
BRANCH = "main"

def _get_token():
    return os.environ.get("GIT_WRITE_TOKEN", "")

def _configure_git():
    try:
        subprocess.run(["git", "config", "user.name", "DO-Agent"],
                       cwd=REPO_DIR, capture_output=True)
        subprocess.run(["git", "config", "user.email", "do-agent@valu.app"],
                       cwd=REPO_DIR, capture_output=True)
    except Exception as e:
        logger.warning(f"[GIT_SYNC] Error configurando git: {e}")

def _needs_push() -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO_DIR
    )
    return result.returncode != 0

def try_sync(file_paths, commit_message="DO: actualizacion automatica de propiedades"):
    token = _get_token()
    if not token:
        return False

    _configure_git()

    try:
        add_result = subprocess.run(
            ["git", "add"] + file_paths,
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=30
        )
        if add_result.returncode != 0:
            logger.error(f"[GIT_SYNC] git add fallo: {add_result.stderr[:200]}")
            return False

        if not _needs_push():
            return True

        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=REPO_DIR, capture_output=True, text=True,
            timeout=30
        )
        if commit_result.returncode != 0:
            logger.error(f"[GIT_SYNC] git commit fallo: {commit_result.stderr[:200]}")
            return False

        auth_url = f"https://giriarte1968:{token}@github.com/giriarte1968/ingresos_familiares.git"
        push_result = subprocess.run(
            ["git", "push", auth_url, BRANCH],
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
