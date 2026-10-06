"""ポモドーロの計時。macOS版 TimerModel と同じ規則です。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Phase(Enum):
    FOCUS = "作業"
    SHORT_BREAK = "短い休憩"
    LONG_BREAK = "長い休憩"

    @property
    def minute_bounds(self) -> tuple[int, int]:
        if self is Phase.FOCUS:
            return (1, 180)
        return (1, 60)


class SoundChoice(Enum):
    CHIME = "chime"
    BEEPS = "beeps"
    TOY_MARCH = "toyMarch"
    BELL = "bell"

    @property
    def title(self) -> str:
        return _SOUND_TITLES[self]

    @property
    def file_name(self) -> str:
        return _SOUND_FILES[self]

    @classmethod
    def from_id(cls, value: str) -> SoundChoice:
        for item in cls:
            if item.value == value:
                return item
        return cls.CHIME


_SOUND_TITLES = {
    SoundChoice.CHIME: "ド・ミ・ソ",
    SoundChoice.BEEPS: "ピピピピ",
    SoundChoice.TOY_MARCH: "おもちゃ風マーチ（オリジナル）",
    SoundChoice.BELL: "やさしいベル",
}

_SOUND_FILES = {
    SoundChoice.CHIME: "timer-chime.wav",
    SoundChoice.BEEPS: "timer-beeps.wav",
    SoundChoice.TOY_MARCH: "timer-toy-march.wav",
    SoundChoice.BELL: "timer-bell.wav",
}


@dataclass
class Effect:
    """再生する音と、出す通知。開始ボタンでは title は空です。"""

    play: SoundChoice | None = None
    title: str = ""
    message: str = ""


def clamp_int(value: object, default: int, low: int, high: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


class TimerEngine:
    def __init__(self) -> None:
        self.phase = Phase.FOCUS
        self.focus_minutes = 25
        self.short_break_minutes = 5
        self.long_break_minutes = 15
        self.focus_start_sound = SoundChoice.CHIME
        self.break_start_sound = SoundChoice.CHIME
        self.break_end_sound = SoundChoice.CHIME
        self.completed_focus = 0
        self.running = False
        self.remaining = self.duration
        self.deadline: float | None = None
        self.remaining_exact: float | None = None

    @property
    def duration(self) -> int:
        if self.phase is Phase.FOCUS:
            return self.focus_minutes * 60
        if self.phase is Phase.SHORT_BREAK:
            return self.short_break_minutes * 60
        return self.long_break_minutes * 60

    @property
    def clock_text(self) -> str:
        minutes, seconds = divmod(max(0, self.remaining), 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 0.0
        ratio = 1.0 - (self.remaining / self.duration)
        return min(1.0, max(0.0, ratio))

    def minutes_for(self, phase: Phase) -> int:
        if phase is Phase.FOCUS:
            return self.focus_minutes
        if phase is Phase.SHORT_BREAK:
            return self.short_break_minutes
        return self.long_break_minutes

    def toggle(self, now: float) -> Effect | None:
        if self.running:
            previous = self.phase
            effect = self.tick(now)
            if self.phase is not previous:
                return effect
            if self.deadline is not None:
                self.remaining_exact = self.deadline - now
            self.deadline = None
            self.running = False
            return None
        sound = self.focus_start_sound if self.phase is Phase.FOCUS else self.break_start_sound
        self.start(now)
        return Effect(play=sound)

    def start(self, now: float) -> None:
        extra = self.remaining_exact if self.remaining_exact is not None else float(self.remaining)
        self.deadline = now + extra
        self.remaining_exact = None
        self.running = True

    def tick(self, now: float) -> Effect | None:
        if self.deadline is None:
            return None
        left = self.deadline - now
        if left <= 1e-4:
            self.remaining = 0
            return self._finish(now)
        self.remaining = math.ceil(left)
        return None

    def reset(self) -> None:
        self.deadline = None
        self.remaining_exact = None
        self.running = False
        self.remaining = self.duration

    def select(self, phase: Phase) -> None:
        self.phase = phase
        self.reset()

    def set_minutes(self, minutes: int, phase: Phase) -> None:
        low, high = phase.minute_bounds
        minutes = clamp_int(minutes, self.minutes_for(phase), low, high)
        if phase is Phase.FOCUS:
            self.focus_minutes = minutes
        elif phase is Phase.SHORT_BREAK:
            self.short_break_minutes = minutes
        else:
            self.long_break_minutes = minutes
        if self.phase is phase:
            self.reset()

    def set_sound(self, choice: SoundChoice, event: str) -> None:
        if event == "focusStart":
            self.focus_start_sound = choice
        elif event == "breakStart":
            self.break_start_sound = choice
        elif event == "breakEnd":
            self.break_end_sound = choice

    def snapshot(self) -> dict[str, int | str]:
        return {
            "focusMinutes": self.focus_minutes,
            "shortBreakMinutes": self.short_break_minutes,
            "longBreakMinutes": self.long_break_minutes,
            "focusStartSound": self.focus_start_sound.value,
            "breakStartSound": self.break_start_sound.value,
            "breakEndSound": self.break_end_sound.value,
        }

    def apply_settings(self, data: dict[str, object]) -> None:
        self.focus_minutes = clamp_int(data.get("focusMinutes"), 25, 1, 180)
        self.short_break_minutes = clamp_int(data.get("shortBreakMinutes"), 5, 1, 60)
        self.long_break_minutes = clamp_int(data.get("longBreakMinutes"), 15, 1, 60)
        self.focus_start_sound = SoundChoice.from_id(str(data.get("focusStartSound") or ""))
        self.break_start_sound = SoundChoice.from_id(str(data.get("breakStartSound") or ""))
        self.break_end_sound = SoundChoice.from_id(str(data.get("breakEndSound") or ""))
        self.phase = Phase.FOCUS
        self.completed_focus = 0
        self.reset()

    def _finish(self, now: float) -> Effect:
        self.deadline = None
        self.running = False
        finished = self.phase
        if finished is Phase.FOCUS:
            self.completed_focus += 1
            self.phase = Phase.LONG_BREAK if self.completed_focus % 4 == 0 else Phase.SHORT_BREAK
            effect = Effect(
                play=self.break_start_sound,
                title="作業おつかれさま！",
                message=f"次は{self.phase.value}です。",
            )
        else:
            self.phase = Phase.FOCUS
            if finished is Phase.LONG_BREAK:
                self.completed_focus %= 4
            effect = Effect(
                play=self.break_end_sound,
                title="休憩終了！",
                message="作業を始めましょう。",
            )
        self.remaining = self.duration
        self.start(now)
        return effect
