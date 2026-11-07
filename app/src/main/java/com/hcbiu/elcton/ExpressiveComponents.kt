package com.hcbiu.elcton

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
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
    contentColor: Color = M3x.Track
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
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default
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
            focusedContainerColor = M3x.SurfaceHigh,
            unfocusedContainerColor = M3x.SurfaceHigh,
            focusedTextColor = M3x.OnSurface,
            unfocusedTextColor = M3x.OnSurface,
            focusedLabelColor = M3x.Track,
            unfocusedLabelColor = M3x.OnSurfaceVariant,
            focusedIndicatorColor = Color.Transparent,
            unfocusedIndicatorColor = Color.Transparent,
            disabledIndicatorColor = Color.Transparent,
            cursorColor = M3x.Track
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
                color = if (isError) M3x.OnErrorContainer else M3x.Track)
            Text(text, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
        }
    }
}

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
