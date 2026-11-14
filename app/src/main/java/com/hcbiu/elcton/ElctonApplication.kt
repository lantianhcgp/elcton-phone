package com.hcbiu.elcton

import android.app.Application
import android.util.Log

/** Passive process-local MCP only: no Activity launches, polling, alarms, or foreground service. */
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
