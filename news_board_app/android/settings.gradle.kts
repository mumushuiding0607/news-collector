// Pre-replace version placeholders and write flutter version props before android plugin configures
gradle.beforeProject {
    if (name == "app") {
        val metadataFile = java.io.File("../../publish/metadata.json")
        if (metadataFile.exists()) {
            val metadata = groovy.json.JsonSlurper().parse(metadataFile) as Map<String, Any>
            val vc = (metadata["version_code"] as Number).toString()
            val vn = metadata["version_name"] as String

            // 写入 local.properties，让 Flutter 插件在 apply() 时能读到正确的版本号
            val localPropsFile = java.io.File("${rootDir}/local.properties")
            val localProps = java.util.Properties()
            if (localPropsFile.exists()) {
                localProps.load(localPropsFile.inputStream())
            }
            localProps["flutter.versionCode"] = vc
            localProps["flutter.versionName"] = vn
            localPropsFile.outputStream().use { localProps.store(it, "") }

            // 直接在 AndroidManifest.xml 的 manifest 标签中添加版本信息
            val manifestFile = java.io.File("${rootDir}/app/src/main/AndroidManifest.xml")
            if (manifestFile.exists()) {
                var content = manifestFile.readText()
                // 如果 manifest 标签还没有 versionCode 和 versionName，则添加
                if (!content.contains("android:versionCode")) {
                    content = content.replace(
                        "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">",
                        "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\"\n    android:versionCode=\"$vc\"\n    android:versionName=\"$vn\">"
                    )
                    manifestFile.writeText(content)
                }
            }
        }
    }
}

pluginManagement {
    val flutterSdkPath =
        run {
            val properties = java.util.Properties()
            file("local.properties").inputStream().use { properties.load(it) }
            val flutterSdkPath = properties.getProperty("flutter.sdk")
            require(flutterSdkPath != null) { "flutter.sdk not set in local.properties" }
            flutterSdkPath
        }

    includeBuild("$flutterSdkPath/packages/flutter_tools/gradle")

       repositories {
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/public") }
        maven { url = uri("https://maven.aliyun.com/repository/gradle-plugin") }
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    id("dev.flutter.flutter-plugin-loader") version "1.0.0"
    id("com.android.application") version "9.0.1" apply false
    id("org.jetbrains.kotlin.android") version "2.3.20" apply false
}

include(":app")
