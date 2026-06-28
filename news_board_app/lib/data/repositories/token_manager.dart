import 'package:shared_preferences/shared_preferences.dart';

/// Token 持久化管理，使用 SharedPreferences
class TokenManager {
  static const String _tokenKey = 'auth_token';
  static SharedPreferences? _prefs;

  static Future<void> _ensureInitialized() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  static Future<void> setToken(String? token) async {
    await _ensureInitialized();
    if (token == null) {
      await _prefs!.remove(_tokenKey);
    } else {
      await _prefs!.setString(_tokenKey, token);
    }
  }

  static Future<String?> getToken() async {
    await _ensureInitialized();
    return _prefs!.getString(_tokenKey);
  }

  static Future<void> clear() async {
    await _ensureInitialized();
    await _prefs!.remove(_tokenKey);
  }
}
