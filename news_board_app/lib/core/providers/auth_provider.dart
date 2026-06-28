import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/repositories/auth_repository.dart';
import 'config_provider.dart';

/// 用户模型
class User {
  final int id;
  final String email;
  final String? phone;
  final String? nickname;
  final String subscriptionLevel;

  const User({
    required this.id,
    required this.email,
    this.phone,
    this.nickname,
    this.subscriptionLevel = 'free',
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int? ?? 0,
      email: json['email'] as String? ?? '',
      phone: json['phone'] as String?,
      nickname: json['nickname'] as String?,
      subscriptionLevel: json['subscriptionLevel'] as String? ?? json['subscription_level'] as String? ?? 'free',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'phone': phone,
    'nickname': nickname,
    'subscription_level': subscriptionLevel,
  };

  User copyWith({
    int? id,
    String? email,
    String? phone,
    String? nickname,
    String? subscriptionLevel,
  }) {
    return User(
      id: id ?? this.id,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      nickname: nickname ?? this.nickname,
      subscriptionLevel: subscriptionLevel ?? this.subscriptionLevel,
    );
  }
}

/// Auth 状态
class AuthState {
  final bool isLoggedIn;
  final User? currentUser;
  final bool isLoading;
  final String? errorMessage;

  const AuthState({
    this.isLoggedIn = false,
    this.currentUser,
    this.isLoading = false,
    this.errorMessage,
  });

  String get subscriptionLevel => currentUser?.subscriptionLevel ?? 'free';
  bool get top2Locked => subscriptionLevel == 'free';
  bool get isPaidUser => subscriptionLevel != 'free';

  AuthState copyWith({
    bool? isLoggedIn,
    User? currentUser,
    bool? isLoading,
    String? errorMessage,
  }) {
    return AuthState(
      isLoggedIn: isLoggedIn ?? this.isLoggedIn,
      currentUser: currentUser ?? this.currentUser,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
    );
  }
}

/// Auth Notifier
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _repo = AuthRepository();

  AuthNotifier() : super(const AuthState()) {
    Future.microtask(() => checkAuth());
  }

  /// 初始化，恢复登录状态
  Future<void> init() async {
    await checkAuth();
  }

  /// 检查登录状态
  Future<void> checkAuth() async {
    state = state.copyWith(isLoading: true);
    try {
      final data = await _repo.getCurrentUser();
      if (data['isLoggedIn'] == true && data['user'] != null) {
        state = AuthState(
          isLoggedIn: true,
          currentUser: User.fromJson(data['user'] as Map<String, dynamic>),
          isLoading: false,
        );
      } else {
        state = const AuthState(isLoggedIn: false, currentUser: null, isLoading: false);
      }
    } catch (e) {
      // 未登录或认证失败，静默处理
      state = const AuthState(isLoggedIn: false, currentUser: null, isLoading: false);
    }
  }

  /// 发送验证码
  Future<bool> sendCode(String email) async {
    await _repo.sendCode(email);
    return true;
  }

  /// 验证码登录
  Future<bool> loginWithCode(String email, String code) async {
    state = AuthState(isLoggedIn: state.isLoggedIn, currentUser: state.currentUser, isLoading: true, errorMessage: null);
    final data = await _repo.loginWithCode(email, code);
    final user = User.fromJson(data['user'] as Map<String, dynamic>);
    state = AuthState(isLoggedIn: true, currentUser: user, isLoading: false);
    return true;
  }

  /// 密码登录
  Future<bool> loginWithPassword(String email, String password) async {
    state = AuthState(isLoggedIn: state.isLoggedIn, currentUser: state.currentUser, isLoading: true, errorMessage: null);
    final data = await _repo.loginWithPassword(email, password);
    final user = User.fromJson(data['user'] as Map<String, dynamic>);
    state = AuthState(isLoggedIn: true, currentUser: user, isLoading: false);
    return true;
  }

  /// 注册
  Future<bool> register(String email, String password, String code) async {
    state = AuthState(isLoggedIn: state.isLoggedIn, currentUser: state.currentUser, isLoading: true, errorMessage: null);
    final data = await _repo.register(email: email, password: password, code: code);
    final user = User.fromJson(data['user'] as Map<String, dynamic>);
    state = AuthState(isLoggedIn: true, currentUser: user, isLoading: false);
    return true;
  }

  /// 登出
  Future<void> logout() async {
    await _repo.logout();
    state = const AuthState(isLoggedIn: false, currentUser: null, isLoading: false);
  }

  /// 发送密码重置验证码
  Future<bool> sendResetCode(String email) async {
    await _repo.sendResetCode(email);
    return true;
  }

  /// 重置密码
  Future<bool> resetPassword(String email, String code, String newPassword) async {
    await _repo.resetPassword(email, code, newPassword);
    return true;
  }

  /// 更新昵称
  Future<bool> updateNickname(String nickname) async {
    await _repo.updateNickname(nickname);
    if (state.currentUser != null) {
      state = state.copyWith(
        currentUser: state.currentUser!.copyWith(nickname: nickname),
      );
    }
    return true;
  }

  /// 更新手机号
  Future<bool> updatePhone(String phone, String code) async {
    await _repo.updatePhone(phone, code);
    if (state.currentUser != null) {
      state = state.copyWith(
        currentUser: state.currentUser!.copyWith(phone: phone),
      );
    }
    return true;
  }

  /// 更新邮箱
  Future<bool> updateEmail(String email, String code) async {
    await _repo.updateEmail(email, code);
    if (state.currentUser != null) {
      state = state.copyWith(
        currentUser: state.currentUser!.copyWith(email: email),
      );
    }
    return true;
  }

  /// 更新密码
  Future<bool> updatePassword(String oldPassword, String newPassword) async {
    await _repo.updatePassword(oldPassword, newPassword);
    return true;
  }

  /// 刷新用户信息（订阅状态变更后调用）
  Future<void> refreshUser() async {
    try {
      final data = await _repo.getCurrentUser();
      if (data['isLoggedIn'] == true && data['user'] != null) {
        state = state.copyWith(
          currentUser: User.fromJson(data['user'] as Map<String, dynamic>),
        );
      }
    } catch (e) {
      // 静默处理
    }
  }
}

/// Provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});

/// 统一订阅权限检查 Provider
/// 返回 true 表示：订阅功能已禁用（白名单） OR 用户已订阅（付费用户）
/// 返回 false 表示：订阅功能已启用 AND 用户为免费用户
final hasSubscriptionAccessProvider = Provider<bool>((ref) {
  final config = ref.watch(configProvider);
  final authState = ref.watch(authProvider);

  // 订阅功能已禁用，所有人都有访问权限
  if (!config.features.subscriptionEnabled) {
    return true;
  }

  // 订阅功能已启用，检查用户是否为付费用户
  return authState.isPaidUser;
});