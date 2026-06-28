import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'token_manager.dart';
import '../../core/providers/config_provider.dart';

class SubscriptionRepository {
  Future<Map<String, String>> _headers() async {
    final token = await TokenManager.getToken();
    final h = <String, String>{'Content-Type': 'application/json'};
    if (token != null) h['Authorization'] = 'Bearer $token';
    return h;
  }

  Future<List<Map<String, dynamic>>> getPlans() async {
    final resp = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/plans'),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    final data = json.decode(resp.body);
    return List<Map<String, dynamic>>.from(data['plans'] ?? []);
  }

  Future<Map<String, dynamic>> getCurrentSubscription() async {
    final resp = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/current'),
      headers: await _headers(),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    return json.decode(resp.body);
  }

  Future<Map<String, dynamic>> getPayMethod() async {
    final resp = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/pay_method'),
      headers: await _headers(),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '获取支付方式失败');
    return data;
  }

  Future<Uint8List> getPersonalQrImage() async {
    final resp = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/personal_qr'),
      headers: await _headers(),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    if (resp.statusCode != 200) throw Exception('获取收款码失败');
    return resp.bodyBytes;
  }

  Future<Map<String, dynamic>> subscribe(String level) async {
    final resp = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/subscribe'),
      headers: await _headers(),
      body: json.encode({'level': level}),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '订阅失败');
    return data;
  }

  Future<Map<String, dynamic>> createOrder(String level) async {
    final resp = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/create_order'),
      headers: await _headers(),
      body: json.encode({'level': level}),
    ).timeout(Duration(seconds: ApiConfig.createOrderTimeout));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '创建订单失败');
    return data;
  }

  Future<Map<String, dynamic>> getOrderStatus(String orderNo) async {
    final resp = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/order/$orderNo'),
      headers: await _headers(),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '查询失败');
    return data;
  }

  Future<Map<String, dynamic>> confirmPayment(String orderNo, String note) async {
    final resp = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/confirm_payment'),
      headers: await _headers(),
      body: json.encode({'order_no': orderNo, 'pay_account_note': note}),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '确认失败');
    return data;
  }

  Future<void> cancel() async {
    final resp = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/api/subscription/cancel'),
      headers: await _headers(),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    final data = json.decode(resp.body);
    if (resp.statusCode != 200) throw Exception(data['detail'] ?? '取消失败');
  }
}