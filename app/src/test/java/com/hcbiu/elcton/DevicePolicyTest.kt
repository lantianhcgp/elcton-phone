package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

class DevicePolicyTest {
    @Test fun capabilitiesDetermineSupportWithoutAModelWhitelist() {
        assertTrue(DevicePolicy.canAttemptSync(true, 1, 1, 0))
        assertTrue(DevicePolicy.canAttemptSync(true, 2, 1, 0))
        assertFalse(DevicePolicy.canAttemptSync(false, 1, 1, 0))
        assertFalse(DevicePolicy.canAttemptSync(true, 0, 1, 0))
    }
}
