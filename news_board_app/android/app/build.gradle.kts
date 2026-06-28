import groovy.json.JsonSlurper
import java.util.Properties

plugins {
    id("com.android.application")
    id("dev.flutter.flutter-gradle-plugin")
}

// ============ 读取 metadata.json ============
val metadataFile = rootProject.layout.projectDirectory.file("../../publish/metadata.json").asFile
val metadata = run {
    val slurper = JsonSlurper()
    slurper.parse(metadataFile) as Map<String, Any>
}

val appName = metadata["app_name"] as String
val appNameEn = metadata["app_name_en"] as String
val versionName = metadata["version_name"] as String
val versionCode = (metadata["version_code"] as Number).toInt()
val privacyPolicyUrl = metadata["privacy_policy_url"] as String
val applicationId = metadata["application_id"] as String

// ============ 预先更新 local.properties 让 Flutter 插件读取 ============
val localProps = Properties()
val localPropsFile = rootProject.layout.projectDirectory.file("local.properties").asFile
if (localPropsFile.exists()) {
    localProps.load(localPropsFile.inputStream())
}
localProps["flutter.versionCode"] = versionCode.toString()
localProps["flutter.versionName"] = versionName
localProps.store(localPropsFile.outputStream(), "")

// ============ 读取 signing.properties ============
val signingProps = Properties()
val signingPropsFile = rootProject.layout.projectDirectory.file("app/signing.properties").asFile
if (signingPropsFile.exists()) {
    signingProps.load(signingPropsFile.inputStream())
}

android {
    namespace = "com.newsboard.news_board"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = applicationId
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = versionCode
        versionName = versionName
        manifestPlaceholders["appName"] = appName
        manifestPlaceholders["privacyPolicyUrl"] = privacyPolicyUrl
    }

    signingConfigs {
        create("release") {
            storeFile = rootProject.file(System.getenv("ANDROID_SDK_KEYSTORE") ?: "C:/android-sdk/news_board.jks")
            storePassword = signingProps["KEY_STORE_PASSWORD"] as String? ?: ""
            keyAlias = signingProps["KEY_ALIAS_NAME"] as String? ?: ""
            keyPassword = signingProps["KEY_ALIAS_PASSWORD"] as String? ?: ""
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

// ============ 打包前自动同步版本 ============
val syncVersion by tasks.registering {
    doLast {
        val python = System.getenv("PYTHON") ?: "python"
        val script = rootProject.layout.projectDirectory.file("../scripts/sync_version.py").asFile
        println("[sync_version] running: $script")
        val result = ProcessBuilder(listOf(python, script.absolutePath))
            .redirectError(ProcessBuilder.Redirect.INHERIT)
            .redirectOutput(ProcessBuilder.Redirect.INHERIT)
            .start()
        val exitCode = result.waitFor()
        if (exitCode != 0) {
            throw GradleException("sync_version.py failed with exit code $exitCode")
        }
    }
}

// ============ 打包前自动同步图标 ============
val syncIcon by tasks.registering {
    doLast {
        val python = System.getenv("PYTHON") ?: "python"
        val script = rootProject.layout.projectDirectory.file("../scripts/sync_icon.py").asFile
        println("[sync_icon] running: $script")
        val result = ProcessBuilder(listOf(python, script.absolutePath))
            .redirectError(ProcessBuilder.Redirect.INHERIT)
            .redirectOutput(ProcessBuilder.Redirect.INHERIT)
            .start()
        val exitCode = result.waitFor()
        if (exitCode != 0) {
            throw GradleException("sync_icon.py failed with exit code $exitCode")
        }
    }
}

tasks.preBuild {
    dependsOn(syncVersion, syncIcon)
}