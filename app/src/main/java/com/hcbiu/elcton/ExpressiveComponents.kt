package com.hcbiu.elcton

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/** Presentation-only containers. Callers retain all state and business callbacks. */
@Composable
internal fun ExpressivePanel(
    modifier: Modifier = Modifier,
    color: Color = M3x.Surface,
    contentColor: Color = M3x.OnSurface,
    content: @Composable ColumnScope.() -> Unit
) {
    Surface(modifier = modifier.fillMaxWidth(), shape = M3x.Panel, color = color, contentColor = contentColor) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp), content = content)
    }
}

@Composable
internal fun ExpressivePill(
    label: String,
    modifier: Modifier = Modifier,
    color: Color = M3x.SurfaceHigh,
    contentColor: Color = M3x.Ink
) {
    Surface(modifier = modifier, shape = M3x.Pill, color = color, contentColor = contentColor) {
        Text(label, style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun ExpressiveField(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    label: @Composable (() -> Unit)? = null,
    singleLine: Boolean = false,
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    containerColor: Color = M3x.SurfaceHigh,
    contentColor: Color = M3x.OnSurface,
    labelColor: Color = M3x.OnSurfaceVariant
) {
    TextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier,
        label = label,
        singleLine = singleLine,
        keyboardOptions = keyboardOptions,
        shape = M3x.Field,
        colors = TextFieldDefaults.colors(
            focusedContainerColor = containerColor,
            unfocusedContainerColor = containerColor,
            focusedTextColor = contentColor,
            unfocusedTextColor = contentColor,
            focusedLabelColor = contentColor,
            unfocusedLabelColor = labelColor,
            focusedIndicatorColor = Color.Transparent,
            unfocusedIndicatorColor = Color.Transparent,
            disabledIndicatorColor = Color.Transparent,
            cursorColor = contentColor
        )
    )
}

@Composable
internal fun ExpressiveNotice(text: String, isError: Boolean, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier.fillMaxWidth(), shape = M3x.Field,
        color = if (isError) M3x.ErrorContainer else M3x.SurfaceHigh,
        contentColor = if (isError) M3x.OnErrorContainer else M3x.OnSurfaceVariant
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(if (isError) "!" else "•", style = MaterialTheme.typography.titleMedium,
                color = if (isError) M3x.OnErrorContainer else M3x.Ink)
            Text(text, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
        }
    }
}

/** Theme is independent of semester editing and all import/export actions. */
@Composable
internal fun ThemeOptions() {
    val preference = LocalThemePreference.current
    ExpressivePanel(modifier = Modifier.testTag("theme-options")) {
        SectionHeading("外观", "主题")
        Row(Modifier.fillMaxWidth().selectableGroup(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ThemeMode.values().forEach { mode ->
                val selected = preference.mode == mode
                Surface(
                    color = if (selected) M3x.PrimaryContainer else M3x.SurfaceHigh,
                    contentColor = if (selected) M3x.OnPrimaryContainer else M3x.OnSurfaceVariant,
                    shape = M3x.Field,
                    modifier = Modifier.weight(1f).heightIn(min = 84.dp)
                        .testTag("theme-${mode.name.lowercase()}")
                        .selectable(selected = selected, role = Role.RadioButton, onClick = { preference.select(mode) })
                ) {
                    Column(Modifier.padding(horizontal = 6.dp, vertical = 12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(if (selected) "✓" else "○", style = MaterialTheme.typography.titleMedium)
                        Text(mode.label, style = MaterialTheme.typography.labelMedium)
                    }
                }
            }
        }
        Text(when (preference.mode) {
            ThemeMode.LIGHT -> "亮色为默认主题，选中后立即生效。"
            ThemeMode.DARK -> "暗色主题，选中后立即生效。"
            ThemeMode.SYSTEM -> "主题随系统的深浅色设置自动切换。"
        }, style = MaterialTheme.typography.bodySmall, color = M3x.OnSurfaceVariant)
        Text("配色", style = MaterialTheme.typography.labelLarge, color = M3x.Ink)
        val dark = when (preference.mode) {
            ThemeMode.LIGHT -> false
            ThemeMode.DARK -> true
            ThemeMode.SYSTEM -> isSystemInDarkTheme()
        }
        Column(Modifier.fillMaxWidth().selectableGroup(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            ThemePalette.values().toList().chunked(3).forEach { row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { palette ->
                        val selected = preference.palette == palette
                        val preview = expressiveColorScheme(palette, dark)
                        Surface(
                            color = if (selected) M3x.PrimaryContainer else M3x.SurfaceHigh,
                            contentColor = if (selected) M3x.OnPrimaryContainer else M3x.OnSurface,
                            shape = M3x.Field,
                            border = BorderStroke(if (selected) 2.dp else 1.dp,
                                if (selected) M3x.Ink else MaterialTheme.colorScheme.outlineVariant.copy(alpha = .35f)),
                            modifier = Modifier.weight(1f).heightIn(min = 60.dp)
                                .testTag("palette-${palette.name.lowercase()}")
                                .selectable(selected = selected, role = Role.RadioButton,
                                    onClick = { preference.selectPalette(palette) })
                        ) {
                            Row(Modifier.padding(horizontal = 12.dp, vertical = 14.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                Surface(shape = CircleShape, color = preview.primary, contentColor = preview.onPrimary) {
                                    Box(Modifier.size(24.dp), contentAlignment = Alignment.Center) {
                                        if (selected) Text("✓", style = MaterialTheme.typography.labelMedium)
                                    }
                                }
                                Text(palette.label, style = MaterialTheme.typography.labelLarge)
                            }
                        }
                    }
                }
            }
        }
        Text("配色与主题独立，选中后立即生效并自动保存。",
            style = MaterialTheme.typography.bodySmall, color = M3x.OnSurfaceVariant)
    }
}

/** The stored colorIndex stays untouched; presentation only mixes business hues into tonal surfaces. */
@Composable
internal fun tonalCourseColor(color: Color): Color =
    color.copy(alpha = if (MaterialTheme.colorScheme.background.luminance() < .5f) .30f else .46f)
        .compositeOver(MaterialTheme.colorScheme.surfaceContainerHighest)

/** Decorative calendar; no fabricated course, progress, or connection state. */
@Composable
internal fun CalendarArtwork(modifier: Modifier = Modifier, color: Color = M3x.Brand) {
    Canvas(modifier.size(56.dp)) {
        val u = size.width / 12f
        val stroke = u * .5f
        drawRoundRect(color, Offset(u * 1.5f, u * 2f), Size(u * 9f, u * 8.5f),
            CornerRadius(u * 1.6f), style = Stroke(stroke))
        drawLine(color, Offset(u * 1.6f, u * 4.8f), Offset(u * 10.4f, u * 4.8f), stroke)
        for (x in listOf(4f, 8f)) drawLine(color, Offset(u * x, u), Offset(u * x, u * 3f), stroke, StrokeCap.Round)
        drawRoundRect(color, Offset(u * 3.3f, u * 6.2f), Size(u * 2.1f, u * 2.1f), CornerRadius(u * .55f))
        drawCircle(color.copy(alpha = .45f), u * .55f, Offset(u * 7.8f, u * 7.25f))
    }
}

@Composable
internal fun SectionHeading(title: String, subtitle: String? = null) {
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        if (subtitle != null) Text(subtitle, style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
