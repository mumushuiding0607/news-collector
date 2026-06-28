import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'dart:convert';
import 'config_provider.dart' show ApiConfig;
import '../router/app_router.dart';
import '../../presentation/pages/download_page.dart';

/// 应用版本配置
class AppVersionConfig {
  final String latestVersion;
  final int latestBuild;
  final String minRequiredVersion;
  final int minRequiredBuild;
  final String? updateUrl;
  final String updateDescription;
  final bool forceUpdate;
  final String channel;
  final String currentVersion;
  final int currentBuild;

  const AppVersionConfig({
    this.latestVersion = '',
    this.latestBuild = 0,
    this.minRequiredVersion = '',
    this.minRequiredBuild = 0,
    this.updateUrl,
    this.updateDescription = '',
    this.forceUpdate = false,
    this.channel = 'self_hosted',
    this.currentVersion = '',
    this.currentBuild = 0,
  });

  /// 显示用：当前版本
  String get currentVersionDisplay =>
      currentVersion.isNotEmpty ? currentVersion : '未知';

  /// 显示用：最新版本
  String get latestVersionDisplay =>
      latestVersion.isNotEmpty ? latestVersion : '未知';

  factory AppVersionConfig.fromJson(Map<String, dynamic> json) {
    return AppVersionConfig(
      latestVersion: json['latest_version'] as String? ?? '',
      latestBuild: json['latest_build'] as int? ?? 0,
      minRequiredVersion: json['min_required_version'] as String? ?? '',
      minRequiredBuild: json['min_required_build'] as int? ?? 0,
      updateUrl: json['update_url'] as String?,
      updateDescription: json['update_description'] as String? ?? '',
      forceUpdate: json['force_update'] as bool? ?? false,
      channel: json['channel'] as String? ?? 'self_hosted',
    );
  }
}

/// 版本检查状态
enum VersionCheckStatus { idle, checking, updateAvailable, upToDate, error }

/// 版本检查结果
class VersionCheckResult {
  final VersionCheckStatus status;
  final AppVersionConfig? config;
  final String? errorMessage;

  const VersionCheckResult({
    this.status = VersionCheckStatus.idle,
    this.config,
    this.errorMessage,
  });
}

/// 版本检查 Notifier
class VersionNotifier extends StateNotifier<VersionCheckResult> {
  VersionNotifier() : super(const VersionCheckResult());

  /// 获取当前版本信息（从 pubspec.yaml 动态读取）
  Future<String> get currentVersion async {
    final info = await PackageInfo.fromPlatform();
    return info.version;
  }

  Future<int> get currentBuild async {
    // 读 APK 内嵌的 versionCode（pubspec / metadata 的 version_code）。
    // 旧版硬编码 1 → 即便后端 latestBuild 递增了，_needsUpdate 比较时永远 1<latest，
    // 老用户装了新版后再次检查更新仍被判定"非最新"，反复弹更新框。
    final info = await PackageInfo.fromPlatform();
    return int.tryParse(info.buildNumber) ?? 1;
  }

  /// 检查更新
  Future<void> checkForUpdate() async {
    state = const VersionCheckResult(status: VersionCheckStatus.checking);

    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}/api/config/version');
      final response = await http.get(uri).timeout(
        const Duration(seconds: 10),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final config = AppVersionConfig.fromJson(data);
        // 注入当前版本信息（动态读取）
        final currentVer = await currentVersion;
        final currentBld = await currentBuild;

        // 调试日志
        print('[VersionCheck] latestVersion=${config.latestVersion}, latestBuild=${config.latestBuild}');
        print('[VersionCheck] currentVersion=$currentVer, currentBuild=$currentBld');

        final configWithCurrent = AppVersionConfig(
          latestVersion: config.latestVersion,
          latestBuild: config.latestBuild,
          minRequiredVersion: config.minRequiredVersion,
          minRequiredBuild: config.minRequiredBuild,
          updateUrl: config.updateUrl,
          updateDescription: config.updateDescription,
          forceUpdate: config.forceUpdate,
          channel: config.channel,
          currentVersion: currentVer,
          currentBuild: currentBld,
        );

        // 比较版本
        final needs = _needsUpdate(configWithCurrent);
        print('[VersionCheck] _needsUpdate=$needs');

        if (needs) {
          state = VersionCheckResult(
            status: VersionCheckStatus.updateAvailable,
            config: configWithCurrent,
          );
          print('[VersionCheck] state set to updateAvailable');
        } else {
          state = const VersionCheckResult(status: VersionCheckStatus.upToDate);
          print('[VersionCheck] state set to upToDate');
        }
      } else {
        state = const VersionCheckResult(status: VersionCheckStatus.error);
        print('[VersionCheck] state set to error: HTTP ${response.statusCode}');
      }
    } catch (e) {
      state = VersionCheckResult(
        status: VersionCheckStatus.error,
        errorMessage: e.toString(),
      );
      print('[VersionCheck] state set to error: $e');
    }
  }

  /// 判断是否需要更新
  bool _needsUpdate(AppVersionConfig config) {
    print('[VersionCheck] _needsUpdate: currentVersion=${config.currentVersion} vs latestVersion=${config.latestVersion}');
    // 仅通过版本号判断
    return config.currentVersion.compareTo(config.latestVersion) < 0;
  }

  /// 启动更新（打开下载链接或应用市场）
  Future<void> launchUpdate(AppVersionConfig config) async {
    String? url = config.updateUrl;

    if (url == null || url.isEmpty) {
      // 根据渠道构建应用市场链接
      switch (config.channel) {
        case 'huawei':
          // 华为应用市场 Deep Link
          // final appId = 'xxx'; // 从配置获取
          // url = 'appgallery://com.huawei.appmarket?productId=$appId';
          break;
        case 'xiaomi':
          // 小米应用市场
          // final packageName = 'com.example.newsboard';
          // url = 'mimarket://details?id=$packageName';
          break;
      }
    }

    if (url != null && url.isNotEmpty) {
      final uri = Uri.parse(url);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    }
  }
}

/// Provider
final versionProvider = StateNotifierProvider<VersionNotifier, VersionCheckResult>((ref) {
  return VersionNotifier();
});

/// 更新对话框
class UpdateDialog extends StatelessWidget {
  final AppVersionConfig config;

  const UpdateDialog({super.key, required this.config});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(
        children: [
          Icon(Icons.system_update, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              '发现新版本 v${config.latestVersion}',
              style: const TextStyle(fontSize: 16),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(config.updateDescription.isNotEmpty
              ? config.updateDescription
              : '有新版本可用，建议立即更新'),
          const SizedBox(height: 12),
          Row(
            children: [
              Text(
                '当前版本: ${config.currentVersionDisplay}',
                style: TextStyle(
                  color: Theme.of(context).textTheme.bodySmall?.color,
                  fontSize: 12,
                ),
              ),
              const Spacer(),
              Icon(Icons.arrow_forward, size: 14, color: Theme.of(context).colorScheme.primary),
              const Spacer(),
              Text(
                '最新版本: ${config.latestVersionDisplay}',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.primary,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        if (!config.forceUpdate)
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('稍后再说'),
          ),
        ElevatedButton.icon(
          onPressed: () {
            Navigator.of(context).pop();
            // 打开下载页面（包含华为应用市场和直接下载两种方式）
            openDownloadPage(context);
          },
          icon: const Icon(Icons.download),
          label: const Text('立即更新'),
        ),
      ],
    );
  }
}

/// 显示更新提示对话框（如果需要更新）
Future<void> showUpdateDialogIfNeeded(BuildContext ctx, WidgetRef ref) async {
  final result = ref.read(versionProvider);
  if (result.status == VersionCheckStatus.updateAvailable && result.config != null) {
    // 获取 GoRouter root navigator 的 context（挂载在 MaterialApp 下）
    final navCtx = appRouter.routerDelegate.navigatorKey.currentContext;
    if (navCtx == null) return;
    await showDialog(
      context: navCtx,
      barrierDismissible: !result.config!.forceUpdate,
      builder: (navCtx) => UpdateDialog(config: result.config!),
    );
  }
}
