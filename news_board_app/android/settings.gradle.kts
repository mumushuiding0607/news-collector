// Pre-replace version placeholders before android plugin configures
gradle.beforeProject {
    if (name == "app") {
        val manifestFile = java.io.File("${rootDir}/app/src/main/AndroidManifest.xml")
        val metadataFile = java.io.File("${rootDir}/../../publish/metadata.json")
        if (metadataFile.exists() && manifestFile.exists()) {
            val metadata = groovy.json.JsonSlurper().parse(metadataFile) as Map<String, Any>
            val content = manifestFile.readText()
            val vc = (metadata["version_code"] as Number).toString()
            val vn = metadata["version_name"] as String
            val rewritten = content.replace("__VC__", vc).replace("__VN__", vn)
            manifestFile.writeText(rewritten)
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
