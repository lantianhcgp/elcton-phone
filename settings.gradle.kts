pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral(); maven("https://developer.huawei.com/repo/") }
}
rootProject.name = "elcton-phone"
include(":app")
