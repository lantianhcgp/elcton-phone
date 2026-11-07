package com.hcbiu.elcton

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.colorResource
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
    val Surface = Color(0xFF1D192B)
    val SurfaceHigh = Color(0xFF292338)
    val OnSurface = Color(0xFFF3EDF7)
    val OnSurfaceVariant = Color(0xFFCAC4D0)
    val Accent = Color(0xFF9E7BFF)
    val Track = Color(0xFFD4C7F7)
    val ErrorContainer = Color(0xFF462A2E)
    val OnErrorContainer = Color(0xFFFFDAD6)
    val Panel = RoundedCornerShape(28.dp)
    val Field = RoundedCornerShape(16.dp)
    val Pill = RoundedCornerShape(99.dp)
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
    val background = colorResource(R.color.phone_background)
    MaterialTheme(
        colorScheme = darkColorScheme(
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
            background = background,
            onBackground = M3x.OnSurface,
            surface = M3x.Surface,
            onSurface = M3x.OnSurface,
            surfaceVariant = M3x.SurfaceHigh,
            onSurfaceVariant = M3x.OnSurfaceVariant,
            outline = Color(0xFF938F99),
            outlineVariant = Color(0xFF494253),
            error = Color(0xFFFFB4AB),
            onError = Color(0xFF690005),
            errorContainer = M3x.ErrorContainer,
            onErrorContainer = M3x.OnErrorContainer,
            surfaceContainerLowest = background,
            surfaceContainerLow = M3x.Surface,
            surfaceContainer = M3x.Surface,
            surfaceContainerHigh = M3x.SurfaceHigh,
            surfaceContainerHighest = Color(0xFF342D42)
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
