import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/repositories/auth_repository.dart';

/// 用户模型
class User {
  final int id;
  final String phone;
  final String? nickname;
  final String subscriptionLevel;

  const User({
    required this.id,
    required this.phone,
    this.nickname,
    this.subscriptionLevel = 'free',
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int? ?? 0,
      phone: json['phone'] as String? ?? '',
      nickname: json['nickname'] as String?,
      subscriptionLevel: json['subscriptionLevel'] as String? ?? json['subscription_level'] as String? ?? 'free',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'phone': phone,
    'nickname': nickname,
    'subscription_level': subscriptionLevel,
  };
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

  AuthNotifier() : super(const AuthState());

  /// 检查登录状态
  Future<void> checkAuth() async {
    state = state.copyWith(isLoading: true);
    try {
      final data = await _repo.getCurrentUser();
      if (data['isLoggedIn'] == true && data['user'] != null) {
        state = AuthState(
          isLoggedIn: true,
          currentUser: User.fromJson(data['user'] as Map<String, dynamic>),
        );
      } else {
        state = const AuthState(isLoggedIn: false, currentUser: null);
      }
    } catch (e) {
      state = const AuthState(isLoggedIn: false, currentUser: null);
    }
  }

  /// 发送验证码
  Future<bool> sendCode(String phone) async {
    try {
      await _repo.sendCode(phone);
      return true;
    } catch (e) {
      return false;
    }
  }

  /// 验证码登录
  Future<bool> loginWithCode(String phone, String code) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final data = await _repo.loginWithCode(phone, code);
      final user = User.fromJson(data['user'] as Map<String, dynamic>);
      state = AuthState(isLoggedIn: true, currentUser: user);
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString().replaceFirst('Exception: ', ''));
      return false;
    }
  }

  /// 密码登录
  Future<bool> loginWithPassword(String phone, String password) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final data = await _repo.loginWithPassword(phone, password);
      final user = User.fromJson(data['user'] as Map<String, dynamic>);
      state = AuthState(isLoggedIn: true, currentUser: user);
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString().replaceFirst('Exception: ', ''));
      return false;
    }
  }

  /// 注册
  Future<bool> register(String phone, String password, String code) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final data = await _repo.register(phone: phone, password: password, code: code);
      final user = User.fromJson(data['user'] as Map<String, dynamic>);
      state = AuthState(isLoggedIn: true, currentUser: user);
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString().replaceFirst('Exception: ', ''));
      return false;
    }
  }

  /// 登出
  Future<void> logout() async {
    await _repo.logout();
    state = const AuthState(isLoggedIn: false, currentUser: null);
  }

  /// 发送密码重置验证码
  Future<bool> sendResetCode(String email) async {
    try {
      await _repo.sendResetCode(email);
      return true;
    } catch (e) {
      return false;
    }
  }

  /// 重置密码
  Future<bool> resetPassword(String email, String code, String newPassword) async {
    try {
      await _repo.resetPassword(email, code, newPassword);
      return true;
    } catch (e) {
      return false;
    }
  }
}

/// Provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});