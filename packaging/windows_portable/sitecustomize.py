"""Lance FieldLab depuis le runtime Python officiel renommé.

Ce fichier est importé automatiquement par ``site``. Le contrôle sur le nom de
l'exécutable laisse ``python.exe`` utilisable pour le diagnostic et évite de
relancer l'interface dans un éventuel processus enfant.
"""

from pathlib import Path
import sys
import traceback


def _est_lanceur_fieldlab() -> bool:
    return (
        Path(sys.executable).name.casefold() == "fieldlab.exe"
        and len(sys.argv) == 1
    )


if _est_lanceur_fieldlab():
    try:
        from fieldlab.app.main_window import run

        run()
    except BaseException:
        journal = Path(sys.executable).with_name("FieldLab-demarrage.log")
        journal.write_text(traceback.format_exc(), encoding="utf-8")
        raise
