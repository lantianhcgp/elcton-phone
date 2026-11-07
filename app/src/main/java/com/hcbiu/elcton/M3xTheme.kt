package com.hcbiu.elcton

import android.app.Activity
import android.content.Context
import android.content.SharedPreferences
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
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
    val Brand = Color(0xFF6750A4)
    val OnBrand = Color.White
    val PrimaryContainer = Color(0xFFEADDFF)
    val OnPrimaryContainer = Color(0xFF21005D)
    val SecondaryContainer = Color(0xFFFFD8E4)
    val OnSecondaryContainer = Color(0xFF31111D)
    val TertiaryContainer = Color(0xFFE8DEF8)
    val OnTertiaryContainer = Color(0xFF1D192B)
    val Surface: Color @Composable get() = MaterialTheme.colorScheme.surface
    val SurfaceHigh: Color @Composable get() = MaterialTheme.colorScheme.surfaceVariant
    val OnSurface: Color @Composable get() = MaterialTheme.colorScheme.onSurface
    val OnSurfaceVariant: Color @Composable get() = MaterialTheme.colorScheme.onSurfaceVariant
    val Ink: Color @Composable get() = MaterialTheme.colorScheme.primary
    val Accent = Color(0xFF9E7BFF)
    val Track = Color(0xFFD4C7F7)
    val ErrorContainer: Color @Composable get() = MaterialTheme.colorScheme.errorContainer
    val OnErrorContainer: Color @Composable get() = MaterialTheme.colorScheme.onErrorContainer
    val Panel = RoundedCornerShape(28.dp)
    val Field = RoundedCornerShape(16.dp)
    val Pill = RoundedCornerShape(99.dp)
}

internal enum class ThemeMode(val label: String) {
    LIGHT("亮色"), DARK("暗色"), SYSTEM("跟随系统")
}

/** Only presentation preferences; never touches schedule or Wear Engine state. */
internal class ThemePreference(private val preferences: SharedPreferences) {
    var mode by mutableStateOf(
        ThemeMode.values().firstOrNull {
            it.name == preferences.getString("mode", ThemeMode.LIGHT.name)
        } ?: ThemeMode.LIGHT
    )
        private set

    fun select(mode: ThemeMode) {
        this.mode = mode
        preferences.edit().putString("mode", mode.name).apply()
    }
}

internal val LocalThemePreference = staticCompositionLocalOf<ThemePreference> {
    error("ThemeOptions must be inside M3xTheme")
}

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
    val view = LocalView.current
    val window = (context as? Activity)?.window
    val chrome = if (dark) Color(0xFF0C0F15) else Color(0xFFF9F5FF)
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
        colorScheme = if (dark) darkColorScheme(
            primary = M3x.Track,
            onPrimary = M3x.OnPrimaryContainer,
            primaryContainer = M3x.PrimaryContainer,
            onPrimaryContainer = M3x.OnPrimaryContainer,
            secondary = M3x.SecondaryContainer,
            onSecondary = M3x.OnSecondaryContainer,
            secondaryContainer = M3x.SecondaryContainer,
            onSecondaryContainer = M3x.OnSecondaryContainer,
            tertiary = M3x.TertiaryContainer,
            onTertiary = M3x.OnTertiaryContainer,
            tertiaryContainer = M3x.TertiaryContainer,
            onTertiaryContainer = M3x.OnTertiaryContainer,
            background = Color(0xFF0C0F15),
            onBackground = Color(0xFFF3EDF7),
            surface = Color(0xFF1D192B),
            onSurface = Color(0xFFF3EDF7),
            surfaceVariant = Color(0xFF292338),
            onSurfaceVariant = Color(0xFFCAC4D0),
            outline = Color(0xFF938F99),
            outlineVariant = Color(0xFF494253),
            error = Color(0xFFFFB4AB),
            onError = Color(0xFF690005),
            errorContainer = Color(0xFF462A2E),
            onErrorContainer = Color(0xFFFFDAD6),
            surfaceContainerLowest = Color(0xFF0C0F15),
            surfaceContainerLow = Color(0xFF1D192B),
            surfaceContainer = Color(0xFF1D192B),
            surfaceContainerHigh = Color(0xFF292338),
            surfaceContainerHighest = Color(0xFF342D42)
        ) else lightColorScheme(
            primary = M3x.Brand,
            onPrimary = M3x.OnBrand,
            primaryContainer = M3x.PrimaryContainer,
            onPrimaryContainer = M3x.OnPrimaryContainer,
            secondary = Color(0xFF7D5260),
            onSecondary = Color.White,
            secondaryContainer = M3x.SecondaryContainer,
            onSecondaryContainer = M3x.OnSecondaryContainer,
            tertiary = Color(0xFF625B71),
            onTertiary = Color.White,
            tertiaryContainer = M3x.TertiaryContainer,
            onTertiaryContainer = M3x.OnTertiaryContainer,
            background = Color(0xFFF9F5FF),
            onBackground = Color(0xFF21005D),
            surface = Color(0xFFFFFBFF),
            onSurface = Color(0xFF21005D),
            surfaceVariant = Color(0xFFF0EAF7),
            onSurfaceVariant = Color(0xFF625671),
            outline = Color(0xFF797080),
            outlineVariant = Color(0xFFCAC4D0),
            error = Color(0xFFBA1A1A),
            onError = Color.White,
            errorContainer = Color(0xFFFCE7E7),
            onErrorContainer = Color(0xFF690005),
            surfaceContainerLowest = Color.White,
            surfaceContainerLow = Color(0xFFFFFBFF),
            surfaceContainer = Color(0xFFFFFBFF),
            surfaceContainerHigh = Color(0xFFF0EAF7),
            surfaceContainerHighest = Color(0xFFE8DEF8)
        ),
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
