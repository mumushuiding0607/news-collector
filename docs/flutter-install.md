# Flutter 安装与配置教程（PowerShell）

---

## 一、下载 Flutter SDK

### 1.1 下载压缩包

```powershell
# 创建安装目录
New-Item -ItemType Directory -Force -Path D:\flutter

# 下载 Flutter SDK（3.24.0 stable）
Invoke-WebRequest -Uri "https://storage.flutter-io.cn/flutter_infra_release/releases/stable/windows/flutter_windows_3.24.0-stable.zip" -OutFile "D:\flutter\flutter.zip"
```

或使用国内镜像（更快）：

```powershell
Invoke-WebRequest -Uri "https://mirrors.tuna.tsinghua.edu.cn/flutter/flutter_infra_release/releases/stable/windows/flutter_windows_3.24.0-stable.zip" -OutFile "D:\flutter\flutter.zip"
```

### 1.2 解压

```powershell
# 解压到 D:\flutter
Expand-Archive -Path "D:\flutter\flutter.zip" -DestinationPath "D:\flutter" -Force
```

解压后删除压缩包：

```powershell
Remove-Item "D:\flutter\flutter.zip"
```

---

## 二、配置环境变量

### 2.1 添加 PATH

```powershell
# 获取当前用户 PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

# 添加 Flutter bin 目录（如果不存在）
if ($userPath -notlike "*D:\flutter\bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;D:\flutter\bin", "User")
}
```

### 2.2 配置国内镜像（可选但推荐）

```powershell
[Environment]::SetEnvironmentVariable("PUB_HOSTED_URL", "https://pub.flutter-io.cn", "User")
[Environment]::SetEnvironmentVariable("FLUTTER_STORAGE_BASE_URL", "https://storage.flutter-io.cn", "User")
```

### 2.3 刷新环境变量（当前终端生效）

```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
```

---

## 三、验证 Flutter

### 3.1 检查版本

```powershell
flutter --version
```

### 3.2 运行 flutter doctor

```powershell
flutter doctor
```

期望看到 `[✓]` 全部绿色。

---

## 四、Android SDK 配置

### 4.1 下载 Android Studio

```powershell
# 下载 Android Studio
Invoke-WebRequest -Uri "https://dl.google.com/android/studio/install/2024.2.2/android-studio-2024.2.2-windows.exe" -OutFile "$env:TEMP\android-studio.exe"
```

### 4.2 安装 Android Studio（静默模式）

```powershell
Start-Process -FilePath "$env:TEMP\android-studio.exe" -ArgumentList "/S", "/all" -Wait
```

### 4.3 获取 Android SDK 路径

```powershell
$androidSdkPath = "$env:LOCALAPPDATA\Android\Sdk"
```

### 4.4 配置 ANDROID_HOME

```powershell
[Environment]::SetEnvironmentVariable("ANDROID_HOME", $androidSdkPath, "User")
[Environment]::SetEnvironmentVariable("ANDROID_SDK_ROOT", $androidSdkPath, "User")
```

### 4.5 添加 Android SDK 到 PATH

```powershell
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$androidPaths = @(
    "$androidSdkPath\platform-tools",
    "$androidSdkPath\tools",
    "$androidSdkPath\tools\bin"
)
foreach ($p in $androidPaths) {
    if ($userPath -notlike "*$p*") {
        $userPath = "$userPath;$p"
    }
}
[Environment]::SetEnvironmentVariable("Path", $userPath, "User")
```

### 4.6 刷新环境变量

```powershell
$env:ANDROID_HOME = $androidSdkPath
$env:ANDROID_SDK_ROOT = $androidSdkPath
$env:Path = "$androidSdkPath\platform-tools;$androidSdkPath\tools;$env:Path"
```

---

## 五、同意许可协议

```powershell
flutter doctor --android-licenses
```

依次输入 `y` 同意所有许可。

---

## 六、验证完整环境

```powershell
flutter doctor
```

确认输出包含：
```
[✓] Flutter
[✓] Android toolchain
[✓] Chrome (如需 Web 开发)
```

---

## 七、创建第一个项目

### 7.1 创建项目

```powershell
# 进入工作目录
cd D:\workspace

# 创建项目
flutter create --org com.example --project-name news_board .
```

### 7.2 获取依赖

```powershell
flutter pub get
```

### 7.3 运行应用

```powershell
flutter run
```

---

## 八、常用命令速查

```powershell
# 环境检查
flutter doctor

# 创建项目
flutter create --org com.example --project-name 项目名 .

# 获取依赖
flutter pub get

# 代码检查
flutter analyze

# 运行调试
flutter run

# 打包 Debug APK
flutter build apk --debug

# 打包 Release APK
flutter build apk --release

# 查看已连接设备
flutter devices

# 清理构建缓存
flutter clean
```

---

## 九、完整安装脚本（自动执行）

将以下内容保存为 `install-flutter.ps1`，右键选择 **使用 PowerShell 运行**：

```powershell
# ===== Flutter 安装脚本 =====
$ErrorActionPreference = "Stop"

# 1. 创建目录并下载
New-Item -ItemType Directory -Force -Path D:\flutter | Out-Null
Write-Host "[1/6] 下载 Flutter SDK..."
Invoke-WebRequest -Uri "https://mirrors.tuna.tsinghua.edu.cn/flutter/flutter_infra_release/releases/stable/windows/flutter_windows_3.24.0-stable.zip" -OutFile "D:\flutter\flutter.zip"

# 2. 解压
Write-Host "[2/6] 解压..."
Expand-Archive -Path "D:\flutter\flutter.zip" -DestinationPath "D:\flutter" -Force
Remove-Item "D:\flutter\flutter.zip"

# 3. 配置 PATH 和镜像
Write-Host "[3/6] 配置环境变量..."
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*D:\flutter\bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;D:\flutter\bin", "User")
}
[Environment]::SetEnvironmentVariable("PUB_HOSTED_URL", "https://pub.flutter-io.cn", "User")
[Environment]::SetEnvironmentVariable("FLUTTER_STORAGE_BASE_URL", "https://storage.flutter-io.cn", "User")

# 4. 刷新 PATH
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")

# 5. 预下载 Flutter（约5-10分钟）
Write-Host "[4/6] 首次下载 Flutter（约5-10分钟）..."
flutter precache

# 6. 同意许可
Write-Host "[5/6] 同意许可协议..."
flutter doctor --android-licenses

# 7. 验证
Write-Host "[6/6] 验证安装..."
flutter doctor

Write-Host "安装完成！"
```