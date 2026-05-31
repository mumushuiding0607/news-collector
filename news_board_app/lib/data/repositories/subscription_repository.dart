import 'package:http/http.dart' as http;
import 'dart:convert';
import 'token_manager.dart';

class SubscriptionRepository {
  static const String _baseUrl = 'http://localhost:3000';

  Map<String, String> _headers() {
    final token = TokenManager.getToken();
    final h = <String, String>{'Content-Type': 'application/json'};
    if (token != null) h['Authorization'] = 'Bearer $token';
    return h;
  }

  Future<List<Map<String, dynamic>>> getPlans() async {
    final resp = await http.get(
      Uri.parse('$_baseUrl/api/subscription/plans'),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    return List<Map<String, dynamic>>.from(data['plans'] ?? []);
  }

  Future<Map<String, dynamic>> getCurrentSubscription() async {
    final resp = await http.get(
      Uri.parse('$_baseUrl/api/subscription/current'),
      headers: _headers(),
    ).timeout(const Duration(seconds: 10));

    return json.decode(resp.body);
  }

  Future<Map<String, dynamic>> subscribe(String level) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/subscription/subscribe'),
      headers: _headers(),
      body: json.encode({'level': level}),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '订阅失败');
    return data;
  }

  Future<void> cancel() async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/subscription/cancel'),
      headers: _headers(),
    ).timeout(const Duration(seconds: 10));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '取消失败');
  }
}