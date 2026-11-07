#!/usr/bin/env python3
"""Pre-agreed source tracers. Actual UI/cold-process checks are separate APK gates."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / 'app/src/main/java/com/hcbiu/elcton/M3xTheme.kt'
COMPONENTS = ROOT / 'app/src/main/java/com/hcbiu/elcton/ExpressiveComponents.kt'
ACTIVITY = ROOT / 'app/src/main/java/com/hcbiu/elcton/MainActivity.kt'
PALETTES = {'PURPLE': '紫', 'BLUE': '蓝', 'GREEN': '绿', 'TEAL': '青', 'ORANGE': '橙', 'PINK': '粉'}


class PaletteSourceTest(unittest.TestCase):
    def test_six_chinese_palettes_have_orthogonal_immediate_isolated_preferences(self):
        source = THEME.read_text()
        self.assertIn('enum class ThemePalette', source)
        for name, label in PALETTES.items():
            self.assertRegex(source, name + r'\("' + label + r'"')
        self.assertIn('getString("palette", ThemePalette.PURPLE.name)', source)
        self.assertIn('} ?: ThemePalette.PURPLE', source)
        self.assertIn('this.palette = palette', source)
        self.assertIn('putString("palette", palette.name).apply()', source)
        self.assertLess(source.index('this.palette = palette'), source.index('putString("palette", palette.name)'))
        self.assertEqual(1, source.count('putString("mode", mode.name)'))
        self.assertEqual(1, source.count('putString("palette", palette.name)'))
        self.assertEqual(2, source.count('mutableStateOf('))


    def test_twelve_complete_tonal_schemes_and_dynamic_roles(self):
        source = THEME.read_text()
        from qa.ui_only_gate import block
        roles = {'primary', 'onPrimary', 'primaryContainer', 'onPrimaryContainer', 'secondary',
                 'onSecondary', 'secondaryContainer', 'onSecondaryContainer', 'tertiary', 'onTertiary',
                 'tertiaryContainer', 'onTertiaryContainer', 'background', 'onBackground', 'surface',
                 'onSurface', 'surfaceVariant', 'onSurfaceVariant', 'outline', 'outlineVariant',
                 'error', 'onError', 'errorContainer', 'onErrorContainer', 'inverseSurface',
                 'inverseOnSurface', 'inversePrimary', 'scrim', 'surfaceTint', 'surfaceBright',
                 'surfaceDim', 'surfaceContainerLowest', 'surfaceContainerLow', 'surfaceContainer',
                 'surfaceContainerHigh', 'surfaceContainerHighest'}
        for name in PALETTES:
            for mode in ('Light', 'Dark'):
                match = re.search(r'private val ' + name.lower() + mode + r' = (?:light|dark)ColorScheme\(([\s\S]*?)\n\)', source)
                self.assertIsNotNone(match, name + mode + ' missing complete ColorScheme')
                self.assertEqual(roles, set(re.findall(r'^    (\w+) = Color\(0xFF[0-9A-F]{6}\)', match[1], re.M)))
        opening = source.index('{', source.index('internal object M3x'))
        values = block(source, opening)
        for role in ('Brand','OnBrand','PrimaryContainer','OnPrimaryContainer','SecondaryContainer',
                     'OnSecondaryContainer','TertiaryContainer','OnTertiaryContainer','Accent','Track'):
            self.assertRegex(values, r'val ' + role + r': Color @Composable get\(\) = ')
        self.assertIn('expressiveColorScheme(preference.palette, dark)', source)
        self.assertIn('val chrome = colorScheme.background', source)
        self.assertIn('colorScheme = colorScheme', source)

    def test_palette_selector_and_nested_field_are_presentation_only(self):
        components = COMPONENTS.read_text()
        activity = ACTIVITY.read_text()
        self.assertIn('ThemePalette.values().toList().chunked(3)', components)
        self.assertIn('testTag("palette-${palette.name.lowercase()}")', components)
        self.assertIn('preference.selectPalette(palette)', components)
        self.assertIn('Text("配色"', components)
        self.assertIn('shape = CircleShape', components)
        palette_section = components.split('Text("配色"', 1)[1].split('/** The stored colorIndex', 1)[0]
        self.assertIn('role = Role.RadioButton', palette_section)
        self.assertIn('palette-preview-${palette.name.lowercase()}',palette_section)
        self.assertIn('palette-label-${palette.name.lowercase()}',palette_section)
        self.assertIn('selectableGroup()', palette_section)
        self.assertIn('containerColor: Color = M3x.SurfaceHigh', components)
        self.assertIn('contentColor: Color = M3x.OnSurface', components)
        self.assertIn('containerColor=M3x.NestedPrimaryContainer', activity)
        self.assertIn('contentColor=M3x.OnPrimaryContainer', activity)
        self.assertIn('val NestedPrimaryContainer: Color @Composable get()', THEME.read_text())

    def test_course_display_is_tonal_but_color_index_and_delete_actions_are_preserved(self):
        activity = ACTIVITY.read_text()
        self.assertIn('private val colors = listOf(Color(0xFF8FA8FF),Color(0xFFB49BFF),Color(0xFF69C9B6),Color(0xFFE7AD77),Color(0xFFDD91B9),Color(0xFF81BCD9),Color(0xFFA7C57F),Color(0xFFB5BCCA))', activity)
        self.assertIn('color=tonalCourseColor(colors[c.colorIndex])', activity)
        self.assertIn('background(tonalCourseColor(c),CircleShape)', activity)
        self.assertIn('if(color==i)M3x.Ink else Color.Transparent', activity)
        self.assertIn('.semantics { selected = color==i }', activity)
        self.assertIn('this[CourseColorIndexKey] = c.colorIndex', activity)
        self.assertIn('SemanticsPropertyKey<Int>("CourseColorIndex")',COMPONENTS.read_text())
        self.assertNotIn('size(if(color==i)', activity)
        self.assertIn('if(existing!=null)OutlinedButton(onClick={delete=true}', activity)
        self.assertIn('BorderStroke(1.dp,MaterialTheme.colorScheme.error.copy(alpha=.45f))', activity)
        self.assertIn('containerColor=Color.Transparent,contentColor=MaterialTheme.colorScheme.error', activity)
        from qa.ui_only_gate import activity_checks
        import subprocess
        base = subprocess.check_output(['git', 'show', '519f0d5450f77ce4ba757a644b2144607b0a5c06:app/src/main/java/com/hcbiu/elcton/MainActivity.kt'], cwd=ROOT, text=True)
        self.assertEqual([], activity_checks(base, activity))

    def test_palette_capture_refreshes_cache_and_rejects_stale_scene_after_dismissing_ime(self):
        source=(ROOT/'app/src/androidTest/java/com/hcbiu/elcton/PaletteUiTest.kt').read_text()
        self.assertIn('private fun dismissKeyboard()',source)
        self.assertIn('hideSoftInputFromWindow',source)
        self.assertIn('window.insetsController?.hide(WindowInsets.Type.ime())',source)
        self.assertIn('private fun freshHierarchy(file:File)',source)
        # API33 UiAutomation.setServiceInfo explicitly clears its connection cache.
        self.assertIn('automation.serviceInfo=checkNotNull(automation.serviceInfo)',source)
        self.assertEqual(1,source.count('device.dumpWindowHierarchy('))
        self.assertIn('freshHierarchy(xmlBefore)',source)
        self.assertIn('freshHierarchy(xml)',source)
        self.assertIn('sceneMatches(nodes,state)',source)
        self.assertIn('sameBounds(parent,option.getJSONArray("bounds"))',source)
        self.assertIn('sameBounds(parent,state.getJSONArray("deleteBounds"))',source)
        self.assertIn('dismissKeyboard();ui.onNodeWithTag("nav-today")',source)
        self.assertIn('dismissKeyboard()\n        ui.onNodeWithTag("course-save")',source)

    def test_palette_preference_gate_rejects_cross_keys_unknown_keys_and_extra_state(self):
        from qa.ui_only_gate import theme_checks
        source = THEME.read_text()
        self.assertEqual([], theme_checks(source))
        for before, after in [
            ('putString("palette", palette.name)', 'putString("mode", palette.name)'),
            ('putString("palette", palette.name)', 'putString("dataset", palette.name)'),
            ('getString("palette", ThemePalette.PURPLE.name)', 'getString("palette", ThemePalette.BLUE.name)'),
            ('this.palette = palette', 'this.mode = ThemeMode.DARK\n        this.palette = palette'),
        ]:
            self.assertIn(before, source)
            self.assertTrue(theme_checks(source.replace(before, after)), before)
        self.assertTrue(theme_checks(source + '\nvar extra = mutableStateOf(0)'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
