import 'package:http/http.dart' as http;
import 'dart:convert';
import 'token_manager.dart';

class AuthRepository {
  static const String _baseUrl = 'http://localhost:3000';

  Future<Map<String, dynamic>> sendCode(String phone) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/auth/send_code'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'phone': phone}),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    if (resp.statusCode == 200) {
      return {'success': true, 'code': data['code']};
    }
    throw Exception(data['detail'] ?? '发送失败');
  }

  Future<Map<String, dynamic>> register({
    required String phone,
    required String password,
    required String code,
  }) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'phone': phone,
        'password': password,
        'code': code,
      }),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    if (resp.statusCode == 200) {
      TokenManager.setToken(data['token']);
      return data;
    }
    throw Exception(data['detail'] ?? '注册失败');
  }

  Future<Map<String, dynamic>> loginWithCode(String phone, String code) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/auth/login_code'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'phone': phone, 'code': code}),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    if (resp.statusCode == 200) {
      TokenManager.setToken(data['token']);
      return data;
    }
    throw Exception(data['detail'] ?? '登录失败');
  }

  Future<Map<String, dynamic>> loginWithPassword(String phone, String password) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/auth/login_password'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'phone': phone, 'password': password}),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    if (resp.statusCode == 200) {
      TokenManager.setToken(data['token']);
      return data;
    }
    throw Exception(data['detail'] ?? '登录失败');
  }

  Future<Map<String, dynamic>> getCurrentUser() async {
    final token = TokenManager.getToken();
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }

    final resp = await http.get(
      Uri.parse('$_baseUrl/api/auth/current_user'),
      headers: headers,
    ).timeout(const Duration(seconds: 10));

    return json.decode(resp.body);
  }

  Future<void> logout() async {
    final token = TokenManager.getToken();
    if (token == null) return;

    try {
      await http.post(
        Uri.parse('$_baseUrl/api/auth/logout'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 5));
    } finally {
      TokenManager.clear();
    }
  }

  Future<void> sendResetCode(String email) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/auth/send_reset_code'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'email': email}),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '发送失败');
  }

  Future<void> resetPassword(String email, String code, String newPassword) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/auth/reset_password'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'email': email,
        'code': code,
        'new_password': newPassword,
      }),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '重置失败');
  }
}