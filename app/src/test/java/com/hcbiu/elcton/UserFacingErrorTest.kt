package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

class UserFacingErrorTest {
    @Test fun missingHealthIsActionableInChinese() {
        val text=UserFacingError.explain("Health app not exist")
        assertTrue(text.contains("未安装华为运动健康"));assertFalse(text.contains("Exception"))
    }
    @Test fun unknownErrorsDoNotLeakSDKDetailsIntoThePrimaryScreen() {
        val text=UserFacingError.explain("internal something")
        assertFalse(text.contains("internal something"));assertTrue(text.contains("诊断记录"))
    }
}
