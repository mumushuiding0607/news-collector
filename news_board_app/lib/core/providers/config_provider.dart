import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../data/repositories/config_repository.dart';

/// 超时配置
class TimeoutsConfig {
  final int defaultTimeout;
  final int sourceTimeout;
  final int createOrderTimeout;

  const TimeoutsConfig({
    this.defaultTimeout = 10,
    this.sourceTimeout = 30,
    this.createOrderTimeout = 15,
  });

  factory TimeoutsConfig.fromJson(Map<String, dynamic> json) {
    return TimeoutsConfig(
      defaultTimeout: json['default'] as int? ?? 10,
      sourceTimeout: json['source'] as int? ?? 30,
      createOrderTimeout: json['create_order'] as int? ?? 15,
    );
  }
}

/// 四维度标签配置
class DimsLabelsConfig {
  final Map<String, String> labels;

  const DimsLabelsConfig({this.labels = const {}});

  factory DimsLabelsConfig.fromJson(Map<String, dynamic> json) {
    return DimsLabelsConfig(
      labels: Map<String, String>.from(json),
    );
  }

  String getLabel(String key) => labels[key] ?? key;
}

/// 功能开关配置
class FeaturesConfig {
  final bool commentsEnabled;
  final bool feedbackEnabled;
  final bool notificationsEnabled;
  final bool sourceManagementEnabled;
  final bool subscriptionEnabled;

  const FeaturesConfig({
    this.commentsEnabled = true,
    this.feedbackEnabled = true,
    this.notificationsEnabled = false,
    this.sourceManagementEnabled = true,
    this.subscriptionEnabled = true,
  });

  factory FeaturesConfig.fromJson(Map<String, dynamic> json) {
    return FeaturesConfig(
      commentsEnabled: _boolFrom(json['comments_enabled']) ?? true,
      feedbackEnabled: _boolFrom(json['feedback_enabled']) ?? true,
      notificationsEnabled: _boolFrom(json['notifications_enabled']) ?? false,
      sourceManagementEnabled: _boolFrom(json['source_management_enabled']) ?? true,
      subscriptionEnabled: _boolFrom(json['subscription_enabled']) ?? true,
    );
  }

  static bool? _boolFrom(dynamic value) {
    if (value == null) return null;
    if (value is bool) return value;
    if (value is num) return value != 0;
    if (value is String) return value.toLowerCase() == 'true';
    return null;
  }
}

/// UI文本配置
class UiTextsConfig {
  final UiTextsLogin login;
  final UiTextsSubscription subscription;
  final UiTextsNewsList newsList;
  final UiTextsSideDrawer sideDrawer;

  const UiTextsConfig({
    this.login = const UiTextsLogin(),
    this.subscription = const UiTextsSubscription(),
    this.newsList = const UiTextsNewsList(),
    this.sideDrawer = const UiTextsSideDrawer(),
  });

  factory UiTextsConfig.fromJson(Map<String, dynamic> json) {
    return UiTextsConfig(
      login: json['login'] != null
          ? UiTextsLogin.fromJson(json['login'] as Map<String, dynamic>)
          : const UiTextsLogin(),
      subscription: json['subscription'] != null
          ? UiTextsSubscription.fromJson(json['subscription'] as Map<String, dynamic>)
          : const UiTextsSubscription(),
      newsList: json['news_list'] != null
          ? UiTextsNewsList.fromJson(json['news_list'] as Map<String, dynamic>)
          : const UiTextsNewsList(),
      sideDrawer: json['side_drawer'] != null
          ? UiTextsSideDrawer.fromJson(json['side_drawer'] as Map<String, dynamic>)
          : const UiTextsSideDrawer(),
    );
  }
}

class UiTextsLogin {
  final String tabCode;
  final String tabPassword;
  final String hintEmail;
  final String hintCode;
  final String hintPassword;
  final String btnSendCode;
  final String btnLogin;
  final String btnRegister;
  final String linkNoAccount;
  final String linkForgotPassword;

  const UiTextsLogin({
    this.tabCode = '验证码登录',
    this.tabPassword = '密码登录',
    this.hintEmail = '请输入邮箱',
    this.hintCode = '请输入验证码',
    this.hintPassword = '请输入密码',
    this.btnSendCode = '发送验证码',
    this.btnLogin = '登录',
    this.btnRegister = '注册',
    this.linkNoAccount = '没有账号？去注册',
    this.linkForgotPassword = '忘记密码？',
  });

  factory UiTextsLogin.fromJson(Map<String, dynamic> json) {
    return UiTextsLogin(
      tabCode: json['tab_code'] as String? ?? '验证码登录',
      tabPassword: json['tab_password'] as String? ?? '密码登录',
      hintEmail: json['hint_email'] as String? ?? '请输入邮箱',
      hintCode: json['hint_code'] as String? ?? '请输入验证码',
      hintPassword: json['hint_password'] as String? ?? '请输入密码',
      btnSendCode: json['btn_send_code'] as String? ?? '发送验证码',
      btnLogin: json['btn_login'] as String? ?? '登录',
      btnRegister: json['btn_register'] as String? ?? '注册',
      linkNoAccount: json['link_no_account'] as String? ?? '没有账号？去注册',
      linkForgotPassword: json['link_forgot_password'] as String? ?? '忘记密码？',
    );
  }
}

class UiTextsSubscription {
  final String success;
  final String scanQrTitle;
  final String wechatQrTitle;
  final String payNote;

  const UiTextsSubscription({
    this.success = '订阅成功！',
    this.scanQrTitle = '请扫码转账',
    this.wechatQrTitle = '请使用微信扫码支付',
    this.payNote = '付款备注：注册时的邮箱或手机号',
  });

  factory UiTextsSubscription.fromJson(Map<String, dynamic> json) {
    return UiTextsSubscription(
      success: json['success'] as String? ?? '订阅成功！',
      scanQrTitle: json['scan_qr_title'] as String? ?? '请扫码转账',
      wechatQrTitle: json['wechat_qr_title'] as String? ?? '请使用微信扫码支付',
      payNote: json['pay_note'] as String? ?? '付款备注：注册时的邮箱或手机号',
    );
  }
}

class UiTextsNewsList {
  final String tabHot;
  final String tabLatest;
  final String tabHistory;

  const UiTextsNewsList({
    this.tabHot = '热点',
    this.tabLatest = '最新',
    this.tabHistory = '历史',
  });

  factory UiTextsNewsList.fromJson(Map<String, dynamic> json) {
    return UiTextsNewsList(
      tabHot: json['tab_hot'] as String? ?? '热点',
      tabLatest: json['tab_latest'] as String? ?? '最新',
      tabHistory: json['tab_history'] as String? ?? '历史',
    );
  }
}

class UiTextsSideDrawer {
  final String accountManage;
  final String sources;
  final String notifications;
  final String settings;
  final String feedback;
  final String logout;
  final String freeUser;
  final String briefing;

  const UiTextsSideDrawer({
    this.accountManage = '账号管理',
    this.sources = '数据源',
    this.notifications = '消息通知',
    this.settings = '系统设置',
    this.feedback = '意见反馈',
    this.logout = '退出登录',
    this.freeUser = '免费用户',
    this.briefing = '简报',
  });

  factory UiTextsSideDrawer.fromJson(Map<String, dynamic> json) {
    return UiTextsSideDrawer(
      accountManage: json['account_manage'] as String? ?? '账号管理',
      sources: json['sources'] as String? ?? '数据源',
      notifications: json['notifications'] as String? ?? '消息通知',
      settings: json['settings'] as String? ?? '系统设置',
      feedback: json['feedback'] as String? ?? '意见反馈',
      logout: json['logout'] as String? ?? '退出登录',
      freeUser: json['free_user'] as String? ?? '免费用户',
      briefing: json['briefing'] as String? ?? '异动简报',
    );
  }
}

/// 锁定配置
class LockConfig {
  final int freeNewsLimit;
  final String lockTitle;
  final String lockButtonLoggedIn;
  final String lockButtonNotLoggedIn;
  final String subscriptionTitle;

  const LockConfig({
    this.freeNewsLimit = 1,
    this.lockTitle = '订阅后可查看完整内容',
    this.lockButtonLoggedIn = '立即订阅',
    this.lockButtonNotLoggedIn = '登录后订阅',
    this.subscriptionTitle = '订阅服务',
  });

  factory LockConfig.fromJson(Map<String, dynamic> json) {
    return LockConfig(
      freeNewsLimit: json['free_news_limit'] as int? ?? 1,
      lockTitle: json['lock_title'] as String? ?? '订阅后可查看完整内容',
      lockButtonLoggedIn: json['lock_button_logged_in'] as String? ?? '立即订阅',
      lockButtonNotLoggedIn: json['lock_button_not_logged_in'] as String? ?? '登录后订阅',
      subscriptionTitle: json['subscription_title'] as String? ?? '订阅服务',
    );
  }
}

/// 应用配置
class AppConfig {
  final String appName;
  final String appSubtitle;
  final bool smsLoginEnabled;
  final bool passwordLoginEnabled;
  final List<SubscriptionTier> subscriptionTiers;
  final ThemeConfig theme;
  final HomeConfig home;
  final TextsConfig texts;
  final LockConfig lock;
  final TimeoutsConfig timeouts;
  final DimsLabelsConfig dimsLabels;
  final FeaturesConfig features;
  final UiTextsConfig uiTexts;
  final DownloadConfig download;

  const AppConfig({
    this.appName = '热点早知道',
    this.appSubtitle = '市场指南针',
    this.smsLoginEnabled = true,
    this.passwordLoginEnabled = true,
    this.subscriptionTiers = const [],
    this.theme = const ThemeConfig(),
    this.home = const HomeConfig(),
    this.texts = const TextsConfig(),
    this.lock = const LockConfig(),
    this.timeouts = const TimeoutsConfig(),
    this.dimsLabels = const DimsLabelsConfig(),
    this.features = const FeaturesConfig(),
    this.uiTexts = const UiTextsConfig(),
    this.download = const DownloadConfig(),
  });

  factory AppConfig.fromJson(Map<String, dynamic> json) {
    return AppConfig(
      appName: json['app_name'] as String? ?? '热点早知道',
      appSubtitle: json['app_subtitle'] as String? ?? '市场指南针',
      smsLoginEnabled: json['sms_login_enabled'] as bool? ?? true,
      passwordLoginEnabled: json['password_login_enabled'] as bool? ?? true,
      subscriptionTiers: (json['subscription_tiers'] as List<dynamic>?)
          ?.map((t) => SubscriptionTier.fromJson(t as Map<String, dynamic>))
          .toList() ?? [],
      theme: json['theme'] != null
          ? ThemeConfig.fromJson(json['theme'] as Map<String, dynamic>)
          : const ThemeConfig(),
      home: json['home'] != null
          ? HomeConfig.fromJson(json['home'] as Map<String, dynamic>)
          : const HomeConfig(),
      texts: json['texts'] != null
          ? TextsConfig.fromJson(json['texts'] as Map<String, dynamic>)
          : const TextsConfig(),
      lock: json['lock'] != null
          ? LockConfig.fromJson(json['lock'] as Map<String, dynamic>)
          : const LockConfig(),
      timeouts: json['timeouts'] != null
          ? TimeoutsConfig.fromJson(json['timeouts'] as Map<String, dynamic>)
          : const TimeoutsConfig(),
      dimsLabels: json['dims_labels'] != null
          ? DimsLabelsConfig.fromJson(json['dims_labels'] as Map<String, dynamic>)
          : const DimsLabelsConfig(),
      features: json['features'] != null
          ? FeaturesConfig.fromJson(json['features'] as Map<String, dynamic>)
          : const FeaturesConfig(),
      uiTexts: json['ui_texts'] != null
          ? UiTextsConfig.fromJson(json['ui_texts'] as Map<String, dynamic>)
          : const UiTextsConfig(),
      download: json['download'] != null
          ? DownloadConfig.fromJson(json['download'] as Map<String, dynamic>)
          : const DownloadConfig(),
    );
  }
}

/// 下载渠道配置
class DownloadChannel {
  final String name;
  final String icon;
  final String url;
  final bool enabled;

  const DownloadChannel({
    required this.name,
    required this.icon,
    required this.url,
    required this.enabled,
  });

  factory DownloadChannel.fromJson(Map<String, dynamic> json) {
    return DownloadChannel(
      name: json['name'] as String? ?? '',
      icon: json['icon'] as String? ?? 'download',
      url: json['url'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? false,
    );
  }
}

/// 下载配置
class DownloadConfig {
  final List<DownloadChannel> channels;
  final String huaweiAppId;

  const DownloadConfig({this.channels = const [], this.huaweiAppId = ''});

  factory DownloadConfig.fromJson(Map<String, dynamic> json) {
    return DownloadConfig(
      channels: (json['channels'] as List<dynamic>?)
          ?.map((c) => DownloadChannel.fromJson(c as Map<String, dynamic>))
          .toList() ?? [],
      huaweiAppId: json['huawei_app_id'] as String? ?? '',
    );
  }

  /// 获取已启用的渠道
  List<DownloadChannel> get enabledChannels => channels.where((c) => c.enabled && c.url.isNotEmpty).toList();

  /// 获取第一个可用渠道的 URL（用于生成二维码）
  String? get primaryUrl {
    final enabled = enabledChannels;
    return enabled.isNotEmpty ? enabled.first.url : null;
  }

  /// 华为应用市场 APP 版链接
  String? get huaweiAppDeepLink {
    if (huaweiAppId.isEmpty) return null;
    return 'appgallery://com.huawei.appmarket?productId=$huaweiAppId';
  }

  /// 华为应用市场网页版链接
  String? get huaweiAppWebUrl {
    if (huaweiAppId.isEmpty) return null;
    return 'https://appgallery.huawei.com/app/$huaweiAppId';
  }
}

/// 首页配置
class HomeConfig {
  final String title;
  final String subtitle;

  const HomeConfig({
    this.title = '市场指南针',
    this.subtitle = '实时跟踪',
  });

  factory HomeConfig.fromJson(Map<String, dynamic> json) {
    return HomeConfig(
      title: json['title'] as String? ?? '市场指南针',
      subtitle: json['subtitle'] as String? ?? '实时跟踪',
    );
  }
}

/// 文本配置
class TextsConfig {
  final String loading;
  final String retry;
  final String emptyData;
  final String emptyHot;
  final String emptyLatest;

  const TextsConfig({
    this.loading = '加载中...',
    this.retry = '重试',
    this.emptyData = '暂无数据',
    this.emptyHot = '暂无热点新闻',
    this.emptyLatest = '暂无最新新闻',
  });

  factory TextsConfig.fromJson(Map<String, dynamic> json) {
    return TextsConfig(
      loading: json['loading'] as String? ?? '加载中...',
      retry: json['retry'] as String? ?? '重试',
      emptyData: json['empty_data'] as String? ?? '暂无数据',
      emptyHot: json['empty_hot'] as String? ?? '暂无热点新闻',
      emptyLatest: json['empty_latest'] as String? ?? '暂无最新新闻',
    );
  }
}

/// 主题配置
class ThemeConfig {
  final String backgroundStart;
  final String backgroundEnd;
  final String accentRed;
  final String accentRedLight;
  final String accentRedDark;
  final String accentGreen;
  final String accentGold;
  final String textPrimary;
  final String textSecondary;
  final String textMuted;
  final String cardBackground;
  final String cardBorder;
  final String cardBackgroundBearish;
  final String cardBorderBearish;
  final int borderRadius;
  final String glassRed;
  final String glassRedBorder;

  const ThemeConfig({
    this.backgroundStart = '#FF1A0808',
    this.backgroundEnd = '#FF2A1010',
    this.accentRed = '#FFE53935',
    this.accentRedLight = '#FFFF6659',
    this.accentRedDark = '#FFAB000D',
    this.accentGreen = '#FF43A047',
    this.accentGold = '#FFFFB300',
    this.textPrimary = '#FFFFFFFF',
    this.textSecondary = '#FFB0B0B0',
    this.textMuted = '#FF707070',
    this.cardBackground = '#22E53935',
    this.cardBorder = '#44E53935',
    this.cardBackgroundBearish = '#1143A047',
    this.cardBorderBearish = '#2B43A047',
    this.borderRadius = 20,
    this.glassRed = '#33E53935',
    this.glassRedBorder = '#55E53935',
  });

  factory ThemeConfig.fromJson(Map<String, dynamic> json) {
    return ThemeConfig(
      backgroundStart: json['background_start'] as String? ?? '#FF1A0808',
      backgroundEnd: json['background_end'] as String? ?? '#FF2A1010',
      accentRed: json['accent_red'] as String? ?? '#FFE53935',
      accentRedLight: json['accent_red_light'] as String? ?? '#FFFF6659',
      accentRedDark: json['accent_red_dark'] as String? ?? '#FFAB000D',
      accentGreen: json['accent_green'] as String? ?? '#FF43A047',
      accentGold: json['accent_gold'] as String? ?? '#FFFFB300',
      textPrimary: json['text_primary'] as String? ?? '#FFFFFFFF',
      textSecondary: json['text_secondary'] as String? ?? '#FFB0B0B0',
      textMuted: json['text_muted'] as String? ?? '#FF707070',
      cardBackground: json['card_background'] as String? ?? '#22E53935',
      cardBorder: json['card_border'] as String? ?? '#44E53935',
      cardBackgroundBearish: json['card_background_bearish'] as String? ?? '#1143A047',
      cardBorderBearish: json['card_border_bearish'] as String? ?? '#2B43A047',
      borderRadius: json['border_radius'] as int? ?? 20,
      glassRed: json['glass_red'] as String? ?? '#33E53935',
      glassRedBorder: json['glass_red_border'] as String? ?? '#55E53935',
    );
  }

  Color get backgroundStartColor => _parseColor(backgroundStart);
  Color get backgroundEndColor => _parseColor(backgroundEnd);
  Color get accentRedColor => _parseColor(accentRed);
  Color get accentRedLightColor => _parseColor(accentRedLight);
  Color get accentRedDarkColor => _parseColor(accentRedDark);
  Color get accentGreenColor => _parseColor(accentGreen);
  Color get accentGoldColor => _parseColor(accentGold);
  Color get textPrimaryColor => _parseColor(textPrimary);
  Color get textSecondaryColor => _parseColor(textSecondary);
  Color get textMutedColor => _parseColor(textMuted);
  Color get cardBackgroundColor => _parseColor(cardBackground);
  Color get cardBorderColor => _parseColor(cardBorder);
  Color get cardBackgroundBearishColor => _parseColor(cardBackgroundBearish);
  Color get cardBorderBearishColor => _parseColor(cardBorderBearish);
  Color get glassRedColor => _parseColor(glassRed);
  Color get glassRedBorderColor => _parseColor(glassRedBorder);

  Color _parseColor(String hex) {
    final str = hex.replaceFirst('#', '');
    return Color(int.parse('FF$str', radix: 16));
  }

  LinearGradient get backgroundGradient => LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [backgroundStartColor, backgroundEndColor],
  );

  BoxDecoration glassCardDecoration(double radius) => BoxDecoration(
    color: cardBackgroundColor,
    borderRadius: BorderRadius.circular(radius.toDouble()),
    border: Border.all(color: cardBorderColor, width: 1),
    boxShadow: [
      BoxShadow(
        color: Colors.black.withOpacity(0.4),
        blurRadius: 20,
        offset: const Offset(0, 10),
      ),
    ],
  );

  BoxDecoration glassRedCardDecoration(double radius) => BoxDecoration(
    color: glassRedColor,
    borderRadius: BorderRadius.circular(radius.toDouble()),
    border: Border.all(color: glassRedBorderColor, width: 1),
    boxShadow: [
      BoxShadow(
        color: accentRedColor.withOpacity(0.3),
        blurRadius: 20,
        offset: const Offset(0, 10),
      ),
    ],
  );
}

/// 主题模式
enum AppThemeMode { dark, light }

/// 浅色主题配置 - 温暖、精致的报纸风格
final lightThemeConfig = ThemeConfig(
  backgroundStart: '#FFF8F6F3',  // 温暖米白
  backgroundEnd: '#FFF2EDE8',     // 略深的暖灰
  accentRed: '#FFE53935',
  accentRedLight: '#FFFF6659',
  accentRedDark: '#FFAB000D',
  accentGreen: '#FF43A047',
  accentGold: '#FFFFB300',
  textPrimary: '#FF1C1C1E',      // 深灰（非纯黑）
  textSecondary: '#FF5C5C5C',
  textMuted: '#FF9B9B9B',
  cardBackground: '#FFFFFFFF',    // 纯白卡片
  cardBorder: '#FFE8E4DE',       // 暖灰边框
  cardBackgroundBearish: '#1143A047',
  cardBorderBearish: '#2B43A047',
  borderRadius: 20,
  glassRed: '#22E53935',         // 更淡的红色
  glassRedBorder: '#33E53935',
);

/// 主题模式管理器（支持持久化）
class ThemeModeNotifier extends StateNotifier<AppThemeMode> {
  static const _key = 'app_theme_mode';
  final SharedPreferences? _prefs;

  ThemeModeNotifier(this._prefs) : super(_load(_prefs));

  static AppThemeMode _load(SharedPreferences? prefs) {
    if (prefs == null) return AppThemeMode.dark;
    final idx = prefs.getInt(_key) ?? 0;
    return AppThemeMode.values[idx.clamp(0, 1)];
  }

  Future<void> toggle() async {
    state = state == AppThemeMode.dark ? AppThemeMode.light : AppThemeMode.dark;
    await _prefs?.setInt(_key, state.index);
  }

  void setMode(AppThemeMode mode) {
    state = mode;
    _prefs?.setInt(_key, mode.index);
  }
}

/// Provider（需要先初始化 SharedPreferences）
final themeModeProvider = StateNotifierProvider<ThemeModeNotifier, AppThemeMode>((ref) {
  return ThemeModeNotifier(null);
});

/// 当前生效的 ThemeConfig（根据模式合并配置）
final effectiveThemeConfigProvider = Provider<ThemeConfig>((ref) {
  final mode = ref.watch(themeModeProvider);
  final base = ref.watch(configProvider).theme;
  if (mode == AppThemeMode.light) {
    // 用浅色配置覆盖基础配置
    return lightThemeConfig;
  }
  return base;
});

/// 便捷的 theme provider（兼容旧代码）
final effectiveThemeProvider = Provider<ThemeConfig>((ref) {
  return ref.watch(effectiveThemeConfigProvider);
});

class SubscriptionTier {
  final String level;
  final String name;
  final double price;
  final int durationDays;
  final String description;
  final List<String> features;

  const SubscriptionTier({
    required this.level,
    required this.name,
    required this.price,
    required this.durationDays,
    required this.description,
    required this.features,
  });

  factory SubscriptionTier.fromJson(Map<String, dynamic> json) {
    return SubscriptionTier(
      level: json['level'] as String,
      name: json['name'] as String,
      price: (json['price'] as num).toDouble(),
      durationDays: json['duration_days'] as int,
      description: json['description'] as String,
      features: List<String>.from(json['features'] ?? []),
    );
  }
}

/// Config Notifier
class ConfigNotifier extends StateNotifier<AppConfig> {
  final ConfigRepository _repo = ConfigRepository();

  ConfigNotifier() : super(const AppConfig());

  Future<void> load() async {
    try {
      final data = await _repo.getConfig();
      state = AppConfig.fromJson(data);

           // 超时配置已在 ApiConfig.loadFromConfig() 中从 config.json 加载
    } catch (e) {
      // 使用默认值
    }
  }

  /// 刷新配置（从服务器重新加载）
  Future<void> refresh() async {
    await load();
  }

  bool get smsLoginEnabled => state.smsLoginEnabled;
  bool get passwordLoginEnabled => state.passwordLoginEnabled;
  String get appName => state.appName;
  String get appSubtitle => state.appSubtitle;
  List<SubscriptionTier> get tiers => state.subscriptionTiers;
  int get freeNewsLimit => state.lock.freeNewsLimit;
  String get lockTitle => state.lock.lockTitle;
  String get lockButtonLoggedIn => state.lock.lockButtonLoggedIn;
  String get lockButtonNotLoggedIn => state.lock.lockButtonNotLoggedIn;
  String get subscriptionTitle => state.lock.subscriptionTitle;
  TimeoutsConfig get timeouts => state.timeouts;
  DimsLabelsConfig get dimsLabels => state.dimsLabels;
  FeaturesConfig get features => state.features;
  UiTextsConfig get uiTexts => state.uiTexts;
  DownloadConfig get download => state.download;
}

/// Provider
final configProvider = StateNotifierProvider<ConfigNotifier, AppConfig>((ref) {
  return ConfigNotifier();
});

/// 便捷的 theme provider（用于非 ConsumerWidget 场景）
final themeProvider = Provider<ThemeConfig>((ref) {
  return ref.watch(configProvider).theme;
});

/// API配置（全局单例，供Repository使用）
class ApiConfig {
  static String _baseUrl = '';
  static int _defaultTimeout = 10;
  static int _sourceTimeout = 30;
  static int _createOrderTimeout = 15;

  /// 从 config.json 加载配置（应用启动时调用）
  static Future<void> loadFromConfig() async {
    try {
      final jsonStr = await rootBundle.loadString('config.json');
      final json = jsonDecode(jsonStr) as Map<String, dynamic>;

      // 从 .env 读取真实 IP（敏感配置），不放在 config.json 中
      final serverIp = dotenv.env['SERVER_IP'] ?? 'localhost';
      final serverPort = dotenv.env['SERVER_PORT'] ?? '31234';
      final prodBaseUrl = 'http://$serverIp:$serverPort';

      final api = json['api'] as Map<String, dynamic>?;
      if (api != null) {
        _baseUrl = kIsWeb
            ? (api['baseUrl'] as String? ?? 'http://localhost:31234')
            : prodBaseUrl;
      }

      final timeouts = json['timeouts'] as Map<String, dynamic>?;
      if (timeouts != null) {
        _defaultTimeout = timeouts['default'] as int? ?? 10;
        _sourceTimeout = timeouts['source'] as int? ?? 30;
        _createOrderTimeout = timeouts['createOrder'] as int? ?? 15;
      }
    } catch (e) {
      // fallback 到 .env 中的值
      final serverIp = dotenv.env['SERVER_IP'] ?? 'localhost';
      final serverPort = dotenv.env['SERVER_PORT'] ?? '31234';
      _baseUrl = kIsWeb ? 'http://localhost:31234' : 'http://$serverIp:$serverPort';
    }
  }

  static String get baseUrl {
    if (_baseUrl.isEmpty) {
      final serverIp = dotenv.env['SERVER_IP'] ?? 'localhost';
      final serverPort = dotenv.env['SERVER_PORT'] ?? '31234';
      return kIsWeb ? 'http://localhost:31234' : 'http://$serverIp:$serverPort';
    }
    return _baseUrl;
  }
  static int get defaultTimeout => _defaultTimeout;
  static int get sourceTimeout => _sourceTimeout;
  static int get createOrderTimeout => _createOrderTimeout;

  static void setBaseUrl(String url) {
    _baseUrl = url;
  }

  static void setTimeouts({
    required int defaultTimeout,
    required int sourceTimeout,
    required int createOrderTimeout,
  }) {
    _defaultTimeout = defaultTimeout;
    _sourceTimeout = sourceTimeout;
    _createOrderTimeout = createOrderTimeout;
  }
}