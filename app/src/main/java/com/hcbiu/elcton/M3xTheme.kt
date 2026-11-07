package com.hcbiu.elcton

import android.app.Activity
import android.content.Context
import android.content.SharedPreferences
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Flat container colors and generous shapes from lite-widget's m3x design. */
internal object M3x {
    val Brand: Color @Composable get() = MaterialTheme.colorScheme.primary
    val OnBrand: Color @Composable get() = MaterialTheme.colorScheme.onPrimary
    val PrimaryContainer: Color @Composable get() = MaterialTheme.colorScheme.primaryContainer
    val OnPrimaryContainer: Color @Composable get() = MaterialTheme.colorScheme.onPrimaryContainer
    val SecondaryContainer: Color @Composable get() = MaterialTheme.colorScheme.secondaryContainer
    val OnSecondaryContainer: Color @Composable get() = MaterialTheme.colorScheme.onSecondaryContainer
    val TertiaryContainer: Color @Composable get() = MaterialTheme.colorScheme.tertiaryContainer
    val OnTertiaryContainer: Color @Composable get() = MaterialTheme.colorScheme.onTertiaryContainer
    val Surface: Color @Composable get() = MaterialTheme.colorScheme.surface
    val SurfaceHigh: Color @Composable get() = MaterialTheme.colorScheme.surfaceContainerHigh
    val OnSurface: Color @Composable get() = MaterialTheme.colorScheme.onSurface
    val OnSurfaceVariant: Color @Composable get() = MaterialTheme.colorScheme.onSurfaceVariant
    val Ink: Color @Composable get() = MaterialTheme.colorScheme.primary
    val Accent: Color @Composable get() = MaterialTheme.colorScheme.primary
    val Track: Color @Composable get() = MaterialTheme.colorScheme.primaryContainer
    val NestedPrimaryContainer: Color @Composable get() =
        MaterialTheme.colorScheme.surface.copy(alpha = .24f).compositeOver(MaterialTheme.colorScheme.primaryContainer)
    val ErrorContainer: Color @Composable get() = MaterialTheme.colorScheme.errorContainer
    val OnErrorContainer: Color @Composable get() = MaterialTheme.colorScheme.onErrorContainer
    val Panel = RoundedCornerShape(28.dp)
    val Field = RoundedCornerShape(16.dp)
    val Pill = RoundedCornerShape(99.dp)
}

internal enum class ThemeMode(val label: String) {
    LIGHT("亮色"), DARK("暗色"), SYSTEM("跟随系统")
}

internal enum class ThemePalette(val label: String) {
    PURPLE("紫"), BLUE("蓝"), GREEN("绿"), TEAL("青"), ORANGE("橙"), PINK("粉")
}

/** Only presentation preferences; never touches schedule or Wear Engine state. */
internal class ThemePreference(private val preferences: SharedPreferences) {
    var mode by mutableStateOf(
        ThemeMode.values().firstOrNull {
            it.name == preferences.getString("mode", ThemeMode.LIGHT.name)
        } ?: ThemeMode.LIGHT
    )
        private set

    var palette by mutableStateOf(
        ThemePalette.values().firstOrNull {
            it.name == preferences.getString("palette", ThemePalette.PURPLE.name)
        } ?: ThemePalette.PURPLE
    )
        private set

    fun select(mode: ThemeMode) {
        this.mode = mode
        preferences.edit().putString("mode", mode.name).apply()
    }

    fun selectPalette(palette: ThemePalette) {
        this.palette = palette
        preferences.edit().putString("palette", palette.name).apply()
    }
}

internal val LocalThemePreference = staticCompositionLocalOf<ThemePreference> {
    error("ThemeOptions must be inside M3xTheme")
}

/** Static HCT tonal roles; purple light preserves the supplied m3x reference DNA. */
internal fun expressiveColorScheme(palette: ThemePalette, dark: Boolean): ColorScheme = when (palette) {
    ThemePalette.PURPLE -> if (dark) purpleDark else purpleLight
    ThemePalette.BLUE -> if (dark) blueDark else blueLight
    ThemePalette.GREEN -> if (dark) greenDark else greenLight
    ThemePalette.TEAL -> if (dark) tealDark else tealLight
    ThemePalette.ORANGE -> if (dark) orangeDark else orangeLight
    ThemePalette.PINK -> if (dark) pinkDark else pinkLight
}

private val purpleLight = lightColorScheme(
    primary = Color(0xFF6750A4),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFEADDFF),
    onPrimaryContainer = Color(0xFF21005D),
    secondary = Color(0xFF7D5260),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFFFD8E4),
    onSecondaryContainer = Color(0xFF31111D),
    tertiary = Color(0xFF625B71),
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFE8DEF8),
    onTertiaryContainer = Color(0xFF1D192B),
    background = Color(0xFFF9F5FF),
    onBackground = Color(0xFF21005D),
    surface = Color(0xFFFFFBFF),
    onSurface = Color(0xFF21005D),
    surfaceVariant = Color(0xFFF0EAF7),
    onSurfaceVariant = Color(0xFF625671),
    surfaceTint = Color(0xFF65558F),
    inverseSurface = Color(0xFF322F35),
    inverseOnSurface = Color(0xFFF5EFF7),
    inversePrimary = Color(0xFFCFBDFE),
    outline = Color(0xFF797080),
    outlineVariant = Color(0xFFCAC4D0),
    error = Color(0xFFBA1A1A),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFFCE7E7),
    onErrorContainer = Color(0xFF690005),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFFFDF7FF),
    surfaceDim = Color(0xFFDED8E0),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFFFFBFF),
    surfaceContainer = Color(0xFFFFFBFF),
    surfaceContainerHigh = Color(0xFFF0EAF7),
    surfaceContainerHighest = Color(0xFFE8DEF8)
)

private val purpleDark = darkColorScheme(
    primary = Color(0xFFD0BCFF),
    onPrimary = Color(0xFF381E72),
    primaryContainer = Color(0xFF4F378B),
    onPrimaryContainer = Color(0xFFEADDFF),
    secondary = Color(0xFFEFB8C8),
    onSecondary = Color(0xFF492532),
    secondaryContainer = Color(0xFF633B48),
    onSecondaryContainer = Color(0xFFFFD8E4),
    tertiary = Color(0xFFCCC2DC),
    onTertiary = Color(0xFF332D41),
    tertiaryContainer = Color(0xFF4A4458),
    onTertiaryContainer = Color(0xFFE8DEF8),
    background = Color(0xFF0C0F15),
    onBackground = Color(0xFFF3EDF7),
    surface = Color(0xFF1D192B),
    onSurface = Color(0xFFF3EDF7),
    surfaceVariant = Color(0xFF292338),
    onSurfaceVariant = Color(0xFFCAC4D0),
    surfaceTint = Color(0xFFCFBDFE),
    inverseSurface = Color(0xFFE6E0E9),
    inverseOnSurface = Color(0xFF322F35),
    inversePrimary = Color(0xFF65558F),
    outline = Color(0xFF938F99),
    outlineVariant = Color(0xFF494253),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF462A2E),
    onErrorContainer = Color(0xFFFFDAD6),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFF3B383E),
    surfaceDim = Color(0xFF141218),
    surfaceContainerLowest = Color(0xFF0C0F15),
    surfaceContainerLow = Color(0xFF1D192B),
    surfaceContainer = Color(0xFF1D192B),
    surfaceContainerHigh = Color(0xFF292338),
    surfaceContainerHighest = Color(0xFF342D42)
)

private val blueLight = lightColorScheme(
    primary = Color(0xFF3D5F90),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFD5E3FF),
    onPrimaryContainer = Color(0xFF234776),
    secondary = Color(0xFF555F71),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFD9E3F8),
    onSecondaryContainer = Color(0xFF3D4758),
    tertiary = Color(0xFF6E5676),
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFF7D8FF),
    onTertiaryContainer = Color(0xFF553F5D),
    background = Color(0xFFF9F9FF),
    onBackground = Color(0xFF191C20),
    surface = Color(0xFFF9F9FF),
    onSurface = Color(0xFF191C20),
    surfaceVariant = Color(0xFFE0E2EC),
    onSurfaceVariant = Color(0xFF43474E),
    surfaceTint = Color(0xFF3D5F90),
    inverseSurface = Color(0xFF2E3035),
    inverseOnSurface = Color(0xFFF0F0F7),
    inversePrimary = Color(0xFFA6C8FF),
    outline = Color(0xFF74777F),
    outlineVariant = Color(0xFFC4C6CF),
    error = Color(0xFFBA1A1A),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF93000A),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFFF9F9FF),
    surfaceDim = Color(0xFFD9DAE0),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFF3F3FA),
    surfaceContainer = Color(0xFFEDEDF4),
    surfaceContainerHigh = Color(0xFFE7E8EE),
    surfaceContainerHighest = Color(0xFFE1E2E9)
)

private val blueDark = darkColorScheme(
    primary = Color(0xFFA6C8FF),
    onPrimary = Color(0xFF02315F),
    primaryContainer = Color(0xFF234776),
    onPrimaryContainer = Color(0xFFD5E3FF),
    secondary = Color(0xFFBDC7DC),
    onSecondary = Color(0xFF273141),
    secondaryContainer = Color(0xFF3D4758),
    onSecondaryContainer = Color(0xFFD9E3F8),
    tertiary = Color(0xFFDABDE2),
    onTertiary = Color(0xFF3D2846),
    tertiaryContainer = Color(0xFF553F5D),
    onTertiaryContainer = Color(0xFFF7D8FF),
    background = Color(0xFF111318),
    onBackground = Color(0xFFE1E2E9),
    surface = Color(0xFF111318),
    onSurface = Color(0xFFE1E2E9),
    surfaceVariant = Color(0xFF43474E),
    onSurfaceVariant = Color(0xFFC4C6CF),
    surfaceTint = Color(0xFFA6C8FF),
    inverseSurface = Color(0xFFE1E2E9),
    inverseOnSurface = Color(0xFF2E3035),
    inversePrimary = Color(0xFF3D5F90),
    outline = Color(0xFF8D9199),
    outlineVariant = Color(0xFF43474E),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFF37393E),
    surfaceDim = Color(0xFF111318),
    surfaceContainerLowest = Color(0xFF0C0E13),
    surfaceContainerLow = Color(0xFF191C20),
    surfaceContainer = Color(0xFF1D2024),
    surfaceContainerHigh = Color(0xFF282A2F),
    surfaceContainerHighest = Color(0xFF32353A)
)

private val greenLight = lightColorScheme(
    primary = Color(0xFF3E6837),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFBFF0B1),
    onPrimaryContainer = Color(0xFF275022),
    secondary = Color(0xFF53634E),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFD6E8CD),
    onSecondaryContainer = Color(0xFF3C4B37),
    tertiary = Color(0xFF386569),
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFBCEBEF),
    onTertiaryContainer = Color(0xFF1E4D51),
    background = Color(0xFFF8FBF1),
    onBackground = Color(0xFF191D17),
    surface = Color(0xFFF8FBF1),
    onSurface = Color(0xFF191D17),
    surfaceVariant = Color(0xFFDFE4D8),
    onSurfaceVariant = Color(0xFF42493F),
    surfaceTint = Color(0xFF3E6837),
    inverseSurface = Color(0xFF2E322B),
    inverseOnSurface = Color(0xFFEFF2E8),
    inversePrimary = Color(0xFFA3D397),
    outline = Color(0xFF73796E),
    outlineVariant = Color(0xFFC2C8BC),
    error = Color(0xFFBA1A1A),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF93000A),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFFF8FBF1),
    surfaceDim = Color(0xFFD8DBD2),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFF2F5EB),
    surfaceContainer = Color(0xFFECEFE5),
    surfaceContainerHigh = Color(0xFFE6E9E0),
    surfaceContainerHighest = Color(0xFFE0E4DA)
)

private val greenDark = darkColorScheme(
    primary = Color(0xFFA3D397),
    onPrimary = Color(0xFF0F380D),
    primaryContainer = Color(0xFF275022),
    onPrimaryContainer = Color(0xFFBFF0B1),
    secondary = Color(0xFFBACCB2),
    onSecondary = Color(0xFF263422),
    secondaryContainer = Color(0xFF3C4B37),
    onSecondaryContainer = Color(0xFFD6E8CD),
    tertiary = Color(0xFFA0CFD3),
    onTertiary = Color(0xFF00363A),
    tertiaryContainer = Color(0xFF1E4D51),
    onTertiaryContainer = Color(0xFFBCEBEF),
    background = Color(0xFF11140F),
    onBackground = Color(0xFFE0E4DA),
    surface = Color(0xFF11140F),
    onSurface = Color(0xFFE0E4DA),
    surfaceVariant = Color(0xFF42493F),
    onSurfaceVariant = Color(0xFFC2C8BC),
    surfaceTint = Color(0xFFA3D397),
    inverseSurface = Color(0xFFE0E4DA),
    inverseOnSurface = Color(0xFF2E322B),
    inversePrimary = Color(0xFF3E6837),
    outline = Color(0xFF8C9387),
    outlineVariant = Color(0xFF42493F),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFF363A34),
    surfaceDim = Color(0xFF11140F),
    surfaceContainerLowest = Color(0xFF0B0F0A),
    surfaceContainerLow = Color(0xFF191D17),
    surfaceContainer = Color(0xFF1D211B),
    surfaceContainerHigh = Color(0xFF272B25),
    surfaceContainerHighest = Color(0xFF323630)
)

private val tealLight = lightColorScheme(
    primary = Color(0xFF006A65),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFF9DF2EA),
    onPrimaryContainer = Color(0xFF00504C),
    secondary = Color(0xFF4A6361),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFCCE8E5),
    onSecondaryContainer = Color(0xFF324B49),
    tertiary = Color(0xFF48607B),
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFD0E4FF),
    onTertiaryContainer = Color(0xFF304962),
    background = Color(0xFFF4FBF9),
    onBackground = Color(0xFF161D1C),
    surface = Color(0xFFF4FBF9),
    onSurface = Color(0xFF161D1C),
    surfaceVariant = Color(0xFFDAE5E3),
    onSurfaceVariant = Color(0xFF3F4947),
    surfaceTint = Color(0xFF006A65),
    inverseSurface = Color(0xFF2B3231),
    inverseOnSurface = Color(0xFFECF2F0),
    inversePrimary = Color(0xFF81D5CE),
    outline = Color(0xFF6F7978),
    outlineVariant = Color(0xFFBEC9C7),
    error = Color(0xFFBA1A1A),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF93000A),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFFF4FBF9),
    surfaceDim = Color(0xFFD5DBDA),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFEFF5F3),
    surfaceContainer = Color(0xFFE9EFED),
    surfaceContainerHigh = Color(0xFFE3E9E8),
    surfaceContainerHighest = Color(0xFFDDE4E2)
)

private val tealDark = darkColorScheme(
    primary = Color(0xFF81D5CE),
    onPrimary = Color(0xFF003734),
    primaryContainer = Color(0xFF00504C),
    onPrimaryContainer = Color(0xFF9DF2EA),
    secondary = Color(0xFFB0CCC9),
    onSecondary = Color(0xFF1C3533),
    secondaryContainer = Color(0xFF324B49),
    onSecondaryContainer = Color(0xFFCCE8E5),
    tertiary = Color(0xFFB0C9E7),
    onTertiary = Color(0xFF19324A),
    tertiaryContainer = Color(0xFF304962),
    onTertiaryContainer = Color(0xFFD0E4FF),
    background = Color(0xFF0E1514),
    onBackground = Color(0xFFDDE4E2),
    surface = Color(0xFF0E1514),
    onSurface = Color(0xFFDDE4E2),
    surfaceVariant = Color(0xFF3F4947),
    onSurfaceVariant = Color(0xFFBEC9C7),
    surfaceTint = Color(0xFF81D5CE),
    inverseSurface = Color(0xFFDDE4E2),
    inverseOnSurface = Color(0xFF2B3231),
    inversePrimary = Color(0xFF006A65),
    outline = Color(0xFF889391),
    outlineVariant = Color(0xFF3F4947),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFF343A3A),
    surfaceDim = Color(0xFF0E1514),
    surfaceContainerLowest = Color(0xFF090F0F),
    surfaceContainerLow = Color(0xFF161D1C),
    surfaceContainer = Color(0xFF1A2120),
    surfaceContainerHigh = Color(0xFF252B2A),
    surfaceContainerHighest = Color(0xFF2F3635)
)

private val orangeLight = lightColorScheme(
    primary = Color(0xFF8B4F25),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFFFDBC8),
    onPrimaryContainer = Color(0xFF6F3810),
    secondary = Color(0xFF755846),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFFFDBC8),
    onSecondaryContainer = Color(0xFF5C4131),
    tertiary = Color(0xFF616133),
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFE7E5AC),
    onTertiaryContainer = Color(0xFF49491E),
    background = Color(0xFFFFF8F5),
    onBackground = Color(0xFF221A15),
    surface = Color(0xFFFFF8F5),
    onSurface = Color(0xFF221A15),
    surfaceVariant = Color(0xFFF4DED3),
    onSurfaceVariant = Color(0xFF52443C),
    surfaceTint = Color(0xFF8B4F25),
    inverseSurface = Color(0xFF382E29),
    inverseOnSurface = Color(0xFFFFEDE5),
    inversePrimary = Color(0xFFFFB689),
    outline = Color(0xFF84746B),
    outlineVariant = Color(0xFFD7C2B8),
    error = Color(0xFFBA1A1A),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF93000A),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFFFFF8F5),
    surfaceDim = Color(0xFFE7D7CF),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFFFF1EA),
    surfaceContainer = Color(0xFFFCEBE2),
    surfaceContainerHigh = Color(0xFFF6E5DC),
    surfaceContainerHighest = Color(0xFFF0DFD7)
)

private val orangeDark = darkColorScheme(
    primary = Color(0xFFFFB689),
    onPrimary = Color(0xFF512300),
    primaryContainer = Color(0xFF6F3810),
    onPrimaryContainer = Color(0xFFFFDBC8),
    secondary = Color(0xFFE5BFA9),
    onSecondary = Color(0xFF432B1C),
    secondaryContainer = Color(0xFF5C4131),
    onSecondaryContainer = Color(0xFFFFDBC8),
    tertiary = Color(0xFFCBC992),
    onTertiary = Color(0xFF323209),
    tertiaryContainer = Color(0xFF49491E),
    onTertiaryContainer = Color(0xFFE7E5AC),
    background = Color(0xFF1A120D),
    onBackground = Color(0xFFF0DFD7),
    surface = Color(0xFF1A120D),
    onSurface = Color(0xFFF0DFD7),
    surfaceVariant = Color(0xFF52443C),
    onSurfaceVariant = Color(0xFFD7C2B8),
    surfaceTint = Color(0xFFFFB689),
    inverseSurface = Color(0xFFF0DFD7),
    inverseOnSurface = Color(0xFF382E29),
    inversePrimary = Color(0xFF8B4F25),
    outline = Color(0xFF9F8D83),
    outlineVariant = Color(0xFF52443C),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFF413731),
    surfaceDim = Color(0xFF1A120D),
    surfaceContainerLowest = Color(0xFF140D08),
    surfaceContainerLow = Color(0xFF221A15),
    surfaceContainer = Color(0xFF261E19),
    surfaceContainerHigh = Color(0xFF312823),
    surfaceContainerHighest = Color(0xFF3D332D)
)

private val pinkLight = lightColorScheme(
    primary = Color(0xFF8B4A62),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFFFD9E3),
    onPrimaryContainer = Color(0xFF6F334A),
    secondary = Color(0xFF74565F),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFFFD9E3),
    onSecondaryContainer = Color(0xFF5A3F48),
    tertiary = Color(0xFF7D5636),
    onTertiary = Color(0xFFFFFFFF),
    tertiaryContainer = Color(0xFFFFDCC3),
    onTertiaryContainer = Color(0xFF623F21),
    background = Color(0xFFFFF8F8),
    onBackground = Color(0xFF22191C),
    surface = Color(0xFFFFF8F8),
    onSurface = Color(0xFF22191C),
    surfaceVariant = Color(0xFFF2DDE2),
    onSurfaceVariant = Color(0xFF514347),
    surfaceTint = Color(0xFF8B4A62),
    inverseSurface = Color(0xFF372E30),
    inverseOnSurface = Color(0xFFFDEDF0),
    inversePrimary = Color(0xFFFFB0CA),
    outline = Color(0xFF837377),
    outlineVariant = Color(0xFFD5C2C6),
    error = Color(0xFFBA1A1A),
    onError = Color(0xFFFFFFFF),
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF93000A),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFFFFF8F8),
    surfaceDim = Color(0xFFE6D6D9),
    surfaceContainerLowest = Color(0xFFFFFFFF),
    surfaceContainerLow = Color(0xFFFFF0F3),
    surfaceContainer = Color(0xFFFAEAED),
    surfaceContainerHigh = Color(0xFFF4E4E7),
    surfaceContainerHighest = Color(0xFFEFDFE2)
)

private val pinkDark = darkColorScheme(
    primary = Color(0xFFFFB0CA),
    onPrimary = Color(0xFF541D34),
    primaryContainer = Color(0xFF6F334A),
    onPrimaryContainer = Color(0xFFFFD9E3),
    secondary = Color(0xFFE2BDC7),
    onSecondary = Color(0xFF422932),
    secondaryContainer = Color(0xFF5A3F48),
    onSecondaryContainer = Color(0xFFFFD9E3),
    tertiary = Color(0xFFF0BC95),
    onTertiary = Color(0xFF48290C),
    tertiaryContainer = Color(0xFF623F21),
    onTertiaryContainer = Color(0xFFFFDCC3),
    background = Color(0xFF191114),
    onBackground = Color(0xFFEFDFE2),
    surface = Color(0xFF191114),
    onSurface = Color(0xFFEFDFE2),
    surfaceVariant = Color(0xFF514347),
    onSurfaceVariant = Color(0xFFD5C2C6),
    surfaceTint = Color(0xFFFFB0CA),
    inverseSurface = Color(0xFFEFDFE2),
    inverseOnSurface = Color(0xFF372E30),
    inversePrimary = Color(0xFF8B4A62),
    outline = Color(0xFF9E8C91),
    outlineVariant = Color(0xFF514347),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    scrim = Color(0xFF000000),
    surfaceBright = Color(0xFF403739),
    surfaceDim = Color(0xFF191114),
    surfaceContainerLowest = Color(0xFF130C0E),
    surfaceContainerLow = Color(0xFF22191C),
    surfaceContainer = Color(0xFF261D20),
    surfaceContainerHigh = Color(0xFF31282A),
    surfaceContainerHighest = Color(0xFF3C3235)
)

private val ExpressiveTypography = Typography(
    displaySmall = TextStyle(fontSize = 40.sp, lineHeight = 44.sp, fontWeight = FontWeight.Bold),
    headlineLarge = TextStyle(fontSize = 32.sp, lineHeight = 40.sp, fontWeight = FontWeight.SemiBold),
    headlineMedium = TextStyle(fontSize = 30.sp, lineHeight = 38.sp, fontWeight = FontWeight.SemiBold),
    headlineSmall = TextStyle(fontSize = 26.sp, lineHeight = 34.sp, fontWeight = FontWeight.SemiBold),
    titleLarge = TextStyle(fontSize = 22.sp, lineHeight = 30.sp, fontWeight = FontWeight.SemiBold),
    titleMedium = TextStyle(fontSize = 18.sp, lineHeight = 26.sp, fontWeight = FontWeight.SemiBold),
    titleSmall = TextStyle(fontSize = 15.sp, lineHeight = 22.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 22.sp),
    bodySmall = TextStyle(fontSize = 12.sp, lineHeight = 19.sp),
    labelLarge = TextStyle(fontSize = 14.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold),
    labelMedium = TextStyle(fontSize = 12.sp, lineHeight = 18.sp, fontWeight = FontWeight.SemiBold),
    labelSmall = TextStyle(fontSize = 11.sp, lineHeight = 16.sp, fontWeight = FontWeight.Medium)
)

@Composable
internal fun M3xTheme(content: @Composable () -> Unit) {
    val context = LocalContext.current
    val preference = remember(context) {
        ThemePreference(context.getSharedPreferences("ui-theme", Context.MODE_PRIVATE))
    }
    val dark = when (preference.mode) {
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
    }
    val colorScheme = expressiveColorScheme(preference.palette, dark)
    val view = LocalView.current
    val window = (context as? Activity)?.window
    val chrome = colorScheme.background
    SideEffect {
        if (window != null && !view.isInEditMode) {
            window.statusBarColor = chrome.toArgb()
            window.navigationBarColor = chrome.toArgb()
            window.navigationBarDividerColor = chrome.toArgb()
            window.isNavigationBarContrastEnforced = false
            window.isStatusBarContrastEnforced = false
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !dark
                isAppearanceLightNavigationBars = !dark
            }
        }
    }
    CompositionLocalProvider(LocalThemePreference provides preference) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = ExpressiveTypography,
            shapes = Shapes(
                extraSmall = RoundedCornerShape(8.dp),
                small = M3x.Field,
                medium = M3x.Field,
                large = M3x.Panel,
                extraLarge = M3x.Panel
            ),
            content = content
        )
    }
}
