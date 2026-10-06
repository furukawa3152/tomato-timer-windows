import unittest

from tomato_timer.logic import Phase, SoundChoice, TimerEngine


class TimerEngineTests(unittest.TestCase):
    def test_initial_clock(self) -> None:
        engine = TimerEngine()
        self.assertEqual(engine.clock_text, "25:00")
        self.assertEqual(engine.progress, 0)
        self.assertFalse(engine.running)

    def test_start_plays_focus_sound_and_pause_keeps_fraction(self) -> None:
        engine = TimerEngine()
        effect = engine.toggle(0.0)
        self.assertIsNotNone(effect)
        assert effect is not None
        self.assertIs(effect.play, SoundChoice.CHIME)
        self.assertEqual(effect.title, "")
        engine.tick(10.4)
        self.assertEqual(engine.remaining, 1490)
        engine.toggle(10.4)
        self.assertFalse(engine.running)
        self.assertAlmostEqual(engine.remaining_exact or 0, 1489.6, places=3)
        engine.toggle(100.0)
        engine.tick(100.0)
        self.assertEqual(engine.remaining, 1490)
        self.assertTrue(engine.running)

    def test_break_start_uses_break_sound(self) -> None:
        engine = TimerEngine()
        engine.break_start_sound = SoundChoice.BELL
        engine.select(Phase.SHORT_BREAK)
        effect = engine.toggle(0.0)
        assert effect is not None
        self.assertIs(effect.play, SoundChoice.BELL)

    def test_focus_finish_moves_to_short_break_and_keeps_running(self) -> None:
        engine = TimerEngine()
        engine.focus_minutes = 1
        engine.short_break_minutes = 3
        engine.remaining = 60
        engine.break_start_sound = SoundChoice.BEEPS
        engine.toggle(0.0)
        effect = engine.tick(60.0)
        assert effect is not None
        self.assertEqual(effect.title, "作業おつかれさま！")
        self.assertEqual(effect.message, "次は短い休憩です。")
        self.assertIs(effect.play, SoundChoice.BEEPS)
        self.assertIs(engine.phase, Phase.SHORT_BREAK)
        self.assertEqual(engine.completed_focus, 1)
        self.assertEqual(engine.remaining, 180)
        self.assertTrue(engine.running)

    def test_pause_at_exact_end_does_not_cancel_finish(self) -> None:
        engine = TimerEngine()
        engine.remaining = 5
        engine.toggle(0.0)
        effect = engine.toggle(5.0)
        assert effect is not None
        self.assertTrue(engine.running)
        self.assertIs(engine.phase, Phase.SHORT_BREAK)
        self.assertEqual(effect.title, "作業おつかれさま！")

    def test_four_focus_sessions_then_long_break_returns_count_to_zero(self) -> None:
        engine = TimerEngine()
        engine.focus_minutes = 1
        engine.short_break_minutes = 1
        engine.long_break_minutes = 1
        engine.remaining = 60
        now = 0.0
        engine.toggle(now)
        for expected in (1, 2, 3):
            now += 60
            engine.tick(now)
            self.assertIs(engine.phase, Phase.SHORT_BREAK)
            self.assertEqual(engine.completed_focus, expected)
            now += 60
            engine.tick(now)
            self.assertIs(engine.phase, Phase.FOCUS)
            self.assertEqual(engine.completed_focus, expected)
        now += 60
        effect = engine.tick(now)
        assert effect is not None
        self.assertIs(engine.phase, Phase.LONG_BREAK)
        self.assertEqual(engine.completed_focus, 4)
        self.assertEqual(effect.message, "次は長い休憩です。")
        now += 60
        effect = engine.tick(now)
        assert effect is not None
        self.assertEqual(effect.title, "休憩終了！")
        self.assertEqual(effect.message, "作業を始めましょう。")
        self.assertIs(engine.phase, Phase.FOCUS)
        self.assertEqual(engine.completed_focus, 0)
        self.assertTrue(engine.running)

    def test_manual_long_break_keeps_completed_count(self) -> None:
        engine = TimerEngine()
        engine.completed_focus = 2
        engine.long_break_minutes = 1
        engine.select(Phase.LONG_BREAK)
        self.assertFalse(engine.running)
        self.assertEqual(engine.remaining, 60)
        engine.toggle(0.0)
        engine.tick(60.0)
        self.assertIs(engine.phase, Phase.FOCUS)
        self.assertEqual(engine.completed_focus, 2)

    def test_set_minutes_resets_only_current_phase(self) -> None:
        engine = TimerEngine()
        engine.toggle(0.0)
        engine.tick(30.0)
        engine.set_minutes(3, Phase.SHORT_BREAK)
        self.assertTrue(engine.running)
        self.assertEqual(engine.short_break_minutes, 3)
        self.assertEqual(engine.remaining, 1470)
        engine.set_minutes(10, Phase.FOCUS)
        self.assertFalse(engine.running)
        self.assertEqual(engine.remaining, 600)
        self.assertEqual(engine.focus_minutes, 10)

    def test_set_minutes_clamps(self) -> None:
        engine = TimerEngine()
        engine.set_minutes(0, Phase.FOCUS)
        self.assertEqual(engine.focus_minutes, 1)
        engine.set_minutes(999, Phase.SHORT_BREAK)
        self.assertEqual(engine.short_break_minutes, 60)

    def test_select_resets_without_sound(self) -> None:
        engine = TimerEngine()
        engine.toggle(0.0)
        engine.select(Phase.LONG_BREAK)
        self.assertIs(engine.phase, Phase.LONG_BREAK)
        self.assertFalse(engine.running)
        self.assertEqual(engine.clock_text, "15:00")

    def test_settings_round_trip(self) -> None:
        engine = TimerEngine()
        engine.focus_start_sound = SoundChoice.BELL
        engine.break_end_sound = SoundChoice.TOY_MARCH
        data = engine.snapshot()
        self.assertEqual(data["focusStartSound"], "bell")
        self.assertEqual(data["breakEndSound"], "toyMarch")
        other = TimerEngine()
        other.apply_settings({**data, "focusMinutes": 999, "shortBreakMinutes": 0})
        self.assertEqual(other.focus_minutes, 180)
        self.assertEqual(other.short_break_minutes, 1)
        self.assertIs(other.focus_start_sound, SoundChoice.BELL)
        self.assertIs(other.break_end_sound, SoundChoice.TOY_MARCH)
        self.assertEqual(other.clock_text, "180:00")
        unknown = TimerEngine()
        unknown.apply_settings({"breakEndSound": "nope"})
        self.assertIs(unknown.break_end_sound, SoundChoice.CHIME)


if __name__ == "__main__":
    unittest.main()
