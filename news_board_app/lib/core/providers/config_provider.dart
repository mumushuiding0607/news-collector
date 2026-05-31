import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/repositories/config_repository.dart';

/// 应用配置
class AppConfig {
  final String appName;
  final String appSubtitle;
  final bool smsLoginEnabled;
  final bool passwordLoginEnabled;
  final List<SubscriptionTier> subscriptionTiers;

  const AppConfig({
    this.appName = '热点早知道',
    this.appSubtitle = '市场风向标',
    this.smsLoginEnabled = true,
    this.passwordLoginEnabled = true,
    this.subscriptionTiers = const [],
  });

  factory AppConfig.fromJson(Map<String, dynamic> json) {
    return AppConfig(
      appName: json['app_name'] as String? ?? '热点早知道',
      appSubtitle: json['app_subtitle'] as String? ?? '市场风向标',
      smsLoginEnabled: json['sms_login_enabled'] as bool? ?? true,
      passwordLoginEnabled: json['password_login_enabled'] as bool? ?? true,
      subscriptionTiers: (json['subscription_tiers'] as List<dynamic>?)
          ?.map((t) => SubscriptionTier.fromJson(t as Map<String, dynamic>))
          .toList() ?? [],
    );
  }
}

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
    } catch (e) {
      // 使用默认值
    }
  }

  bool get smsLoginEnabled => state.smsLoginEnabled;
  bool get passwordLoginEnabled => state.passwordLoginEnabled;
  String get appName => state.appName;
  String get appSubtitle => state.appSubtitle;
  List<SubscriptionTier> get tiers => state.subscriptionTiers;
}

/// Provider
final configProvider = StateNotifierProvider<ConfigNotifier, AppConfig>((ref) {
  return ConfigNotifier();
});