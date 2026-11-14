package com.hcbiu.elcton

import android.app.Application
import android.util.Log

/** Default passive MCP; foreground sessions start only after explicit user opt-in. */
class ElctonApplication : Application() {
    lateinit var diagnostics: DiagnosticRuntime
        private set

    override fun onCreate() {
        super.onCreate()
        diagnostics = DiagnosticRuntime(filesDir)
        try {
            diagnostics.start()
        } catch (error: Exception) {
            // Observability initialization must never gate normal editing or Wear Engine calls.
            Log.w("ElctonMcp", "Diagnostic MCP unavailable: " + error.javaClass.simpleName)
        }
    }
}
