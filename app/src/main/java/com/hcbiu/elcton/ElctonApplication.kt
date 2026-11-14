package com.hcbiu.elcton

import android.app.Application
import android.util.Log

/** Process-owned shared runtime. SDK clients are lazy; no Activity or pairing prompt is launched. */
class ElctonApplication : Application() {
    lateinit var diagnostics: DiagnosticRuntime
        private set
    private val sharedPhone = lazy { PhoneRuntime(this) }
    val phone: PhoneRuntime get() = sharedPhone.value
    fun cancelPhoneIfInitialized() { if (sharedPhone.isInitialized()) phone.cancelAll() }

    override fun onCreate() {
        super.onCreate()
        diagnostics = DiagnosticRuntime(filesDir)
        diagnostics.attachActions(PhoneMcpTools { name, arguments -> phone.mcp(name, arguments) })
        try {
            diagnostics.start(false)
        } catch (error: Exception) {
            // Diagnostic failure never silently resets courses or starts authorization UI.
            Log.w("ElctonMcp", "Diagnostic MCP unavailable: " + error.javaClass.simpleName)
        }
    }
}
