/// 简单的内存token管理（生产环境应使用 flutter_secure_storage）
class TokenManager {
  static String? _token;

  static void setToken(String? token) => _token = token;
  static String? getToken() => _token;
  static void clear() => _token = null;
}