import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import '../../core/providers/config_provider.dart' show configProvider, ApiConfig, AppConfig;
import '../../core/providers/version_provider.dart' show versionProvider, VersionCheckStatus;

/// 下载页面
class DownloadPage extends ConsumerStatefulWidget {
  const DownloadPage({super.key});

  @override
  ConsumerState<DownloadPage> createState() => _DownloadPageState();
}

class _DownloadPageState extends ConsumerState<DownloadPage> {
  String _version = '';

  @override
  void initState() {
    super.initState();
    _loadVersion();
  }

  Future<void> _loadVersion() async {
    try {
      final packageInfo = await PackageInfo.fromPlatform();
      if (mounted) {
        setState(() {
          _version = packageInfo.version;
        });
      }
    } catch (e) {
      // ignore
    }
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(configProvider);
    final appName = config.appName;
    final appSubtitle = config.appSubtitle;

    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      body: SafeArea(
        child: Column(
          children: [
            // 顶部 App 信息区
            Container(
              padding: const EdgeInsets.symmetric(vertical: 48),
              child: Column(
                children: [
                  // App 图标（从网络加载）
                  Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      color: const Color(0xFF3863F4),
                      borderRadius: BorderRadius.circular(22),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(22),
                      child: Image.network(
                        '${ApiConfig.baseUrl}/img/app_icon.png',
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) {
                          return const Icon(
                            Icons.download_rounded,
                            color: Colors.white,
                            size: 56,
                          );
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                  // 标题：使用 appName
                  Text(
                    appName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  // 副标题
                  Text(
                    appSubtitle,
                    style: const TextStyle(
                      color: Colors.white54,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 8),
                  // 版本号
                  if (_version.isNotEmpty)
                    Text(
                      'V$_version',
                      style: const TextStyle(
                        color: Colors.white38,
                        fontSize: 12,
                      ),
                    ),
                ],
              ),
            ),

            const Spacer(),

            // 应用商店列表
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                children: [
                  // 华为应用市场
                  _DownloadButton(
                    iconWidget: _buildHuaweiIcon(),
                    title: '华为应用市场',
                    subtitle: '官方安全下载',
                    color: const Color(0xFFE53935),
                    onTap: () => _openDownload(config, 'huawei'),
                  ),
                  const SizedBox(height: 12),
                  // 直接下载
                  _DownloadButton(
                    iconData: Icons.download_rounded,
                    iconColor: const Color(0xFFFF6659),
                    title: '普通下载地址',
                    subtitle: '直接下载 APK 文件',
                    color: const Color(0xFFFF6659),
                    onTap: () => _openDownload(config, 'download'),
                  ),
                ],
              ),
            ),

            const Spacer(),

            // 底部提示
            const Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                '安装遇到问题？请尝试普通下载地址',
                style: TextStyle(
                  color: Colors.white38,
                  fontSize: 12,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 构建华为图标
  Widget _buildHuaweiIcon() {
    return Container(
      width: 24,
      height: 24,
      decoration: const BoxDecoration(
        color: Color(0xFFE53935),
        shape: BoxShape.circle,
      ),
      child: ClipOval(
        child: Image.network(
          '${ApiConfig.baseUrl}/img/huawei.svg',
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) {
            return const Center(
              child: Text(
                'H',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  /// 打开下载链接
  Future<void> _openDownload(AppConfig config, String channelType) async {
    String? url;
    final channels = config.download.channels;

    // 查找对应渠道的配置
    for (final channel in channels) {
      if (channel.icon == channelType) {
        url = channel.url;
        break;
      }
    }

    // URL 为空时生成默认链接
    if (url == null || url.isEmpty) {
      switch (channelType) {
        case 'huawei':
          // 使用网页版 URL（更可靠）
          final huaweiAppId = config.download.huaweiAppId;
          if (huaweiAppId.isNotEmpty) {
            url = 'https://appgallery.huawei.com/app/$huaweiAppId';
          } else {
            url = 'https://appgallery.huawei.com/';
          }
          break;
        case 'download':
        default:
          // 获取最新版本号（从版本检查 Provider），而非当前安装版本
          String latestVersion = _version;
          final versionResult = ref.read(versionProvider);
          if (versionResult.status == VersionCheckStatus.updateAvailable &&
              versionResult.config != null) {
            latestVersion = versionResult.config!.latestVersion;
          }
          url = '${ApiConfig.baseUrl}/apk/news_board_$latestVersion.apk';
          break;
      }
    }

    final uri = Uri.parse(url);
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('打开下载页面失败: $e')),
        );
      }
    }
  }
}

/// 下载按钮组件
class _DownloadButton extends StatelessWidget {
  final IconData? iconData;
  final Color? iconColor;
  final Widget? iconWidget;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _DownloadButton({
    this.iconData,
    this.iconColor,
    this.iconWidget,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: color.withValues(alpha: 0.3),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Center(
                  child: iconWidget ?? Icon(iconData, color: iconColor ?? color, size: 24),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: Colors.white54,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: color,
                size: 28,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 打开下载页面的便捷方法
Future<void> openDownloadPage(BuildContext context) {
  return showGeneralDialog(
    context: context,
    barrierDismissible: true,
    barrierLabel: '关闭',
    barrierColor: Colors.black87,
    transitionDuration: const Duration(milliseconds: 300),
    pageBuilder: (_, __, ___) => const DownloadPage(),
  );
}
