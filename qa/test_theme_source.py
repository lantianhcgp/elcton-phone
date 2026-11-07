#!/usr/bin/env python3
"""Source tracers / exact scope gate. Does not replace real APK runtime tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / 'app/src/main/java/com/hcbiu/elcton/M3xTheme.kt'
COMPONENTS = ROOT / 'app/src/main/java/com/hcbiu/elcton/ExpressiveComponents.kt'
ACTIVITY = ROOT / 'app/src/main/java/com/hcbiu/elcton/MainActivity.kt'


class ThemeSourceTest(unittest.TestCase):
    def test_light_palette_is_present_without_deleting_dark_palette(self):
        source = THEME.read_text()
        self.assertRegex(source, r'lightColorScheme\s*\(')
        self.assertRegex(source, r'darkColorScheme\s*\(')
        for color in ('F9F5FF','FFFBFF','F0EAF7','21005D','625671','0C0F15','1D192B','292338'):
            self.assertIn('0xFF'+color, source, color)

    def test_three_modes_are_available_with_light_default_and_isolated_persistence(self):
        source = THEME.read_text()
        self.assertRegex(source, r'enum class ThemeMode[\s\S]+LIGHT\("亮色"\)[\s\S]+DARK\("暗色"\)[\s\S]+SYSTEM\("跟随系统"\)')
        self.assertIn('getSharedPreferences("ui-theme", Context.MODE_PRIVATE)', source)
        self.assertIn('getString("mode", ThemeMode.LIGHT.name)', source)
        self.assertIn('putString("mode", mode.name).apply()', source)
        self.assertIn('isSystemInDarkTheme()', source)
        self.assertIn('CompositionLocalProvider', source)

    def test_theme_pref_gate_rejects_business_namespaces_and_effects(self):
        from qa.ui_only_gate import theme_checks
        source = THEME.read_text()
        self.assertEqual([], theme_checks(source))
        self.assertTrue(theme_checks(source.replace('getSharedPreferences("ui-theme"', 'getSharedPreferences("phone-protocol"')))
        self.assertTrue(theme_checks(source.replace('putString("mode"', 'putString("dataset"')))
        self.assertTrue(theme_checks(source + '\nfun broken(){ ScheduleStore(context).save(book) }'))
        self.assertTrue(theme_checks(source + '\nLaunchedEffect(Unit){ probe.cancel() }'))

    def test_capture_uses_same_xml_without_stale_accessibility_handles(self):
        source = (ROOT/'app/src/androidTest/java/com/hcbiu/elcton/ThemeUiTest.kt').read_text()
        self.assertIn('snapshot(xmlBefore)', source)
        self.assertIn('snapshot(xml)', source)
        self.assertNotIn('device.findObjects(By.pkg(pkg))', source)
        self.assertIn('rendered(picture, xml, after, dark, needsIme)', source)

    def test_settings_exposes_three_accessible_options_after_semester(self):
        activity = ACTIVITY.read_text()
        components = COMPONENTS.read_text()
        self.assertIn('ThemeOptions()', activity)
        self.assertLess(activity.index('第一周按该日期所在的周一起算。'), activity.index('ThemeOptions()'))
        self.assertLess(activity.index('ThemeOptions()'), activity.index('SectionHeading("导入与备份")'))
        self.assertIn('LocalThemePreference.current', components)
        self.assertIn('ThemeMode.values().forEach', components)
        self.assertIn('Role.RadioButton', components)
        self.assertIn('selectableGroup()', components)
        self.assertIn('testTag("theme-${mode.name.lowercase()}")', components)
        self.assertIn('preference.select(mode)', components)
        self.assertNotIn('M3x.Track', components)


if __name__ == '__main__':
    unittest.main(verbosity=2)
