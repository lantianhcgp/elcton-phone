package com.hcbiu.elcton

import org.junit.Assert.*
import org.junit.Test

/** Compiled by the real Android variant. Does not infer version from source text. */
class P2pCandidateBuildTest {
    @Test fun actualGeneratedBuildConfigIsBoundToExplicitBuildProfile() {
        assertEquals("com.hcbiu.elcton", BuildConfig.APPLICATION_ID)
        if (BuildConfig.P2P_READY_CANDIDATE) {
            assertEquals(10, BuildConfig.VERSION_CODE)
            assertEquals("0.2.8", BuildConfig.VERSION_NAME)
        } else {
            assertEquals(8, BuildConfig.VERSION_CODE)
            assertEquals("0.2.6", BuildConfig.VERSION_NAME)
        }
    }
}
