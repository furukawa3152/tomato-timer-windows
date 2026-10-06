"""通知音。読めないときや再生に失敗したときはシステム音を鳴らします。"""

from __future__ import annotations

import winsound
from pathlib import Path

from tomato_timer.logic import SoundChoice

SOUND_DIR = Path(__file__).resolve().parent.parent / "sounds"


def play_sound(choice: SoundChoice) -> None:
    path = SOUND_DIR / choice.file_name
    if not path.is_file():
        _beep()
        return
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
        played = winsound.PlaySound(
            str(path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except RuntimeError:
        played = False
    if not played:
        _beep()


def _beep() -> None:
    try:
        winsound.MessageBeep(winsound.MB_OK)
    except RuntimeError:
        pass
