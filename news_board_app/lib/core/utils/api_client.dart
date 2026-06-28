import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../providers/config_provider.dart';

/// API 错误异常
class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

/// API 客户端 - 统一处理 HTTP 请求和错误检测
/// 所有错误弹窗统一在此处理，调用方无需再处理错误弹窗
class ApiClient {
  /// 全局导航器 key，用于在任意位置显示弹窗
  static final rootNavigatorKey = GlobalKey<NavigatorState>();

  /// 检查响应是否有错误，有则弹窗并抛异常
  static void _checkError(Map<String, dynamic> data, int statusCode) {
    // 优先检查 detail 字段（业务错误）
    final detail = data['detail'];
    if (detail != null && detail.toString().isNotEmpty) {
      _showErrorDialog(detail.toString());
      throw ApiException(detail.toString());
    }
    // HTTP 状态码错误
    if (statusCode >= 400) {
      final msg = data['message'] ?? '请求失败';
      _showErrorDialog(msg);
      throw ApiException(msg);
    }
  }

  /// 显示错误弹窗（幂等：只显示一次）
  static void _showErrorDialog(String message) {
    final ctx = rootNavigatorKey.currentContext;
    if (ctx == null) return;

    // 检查是否已有弹窗显示，避免重复
    Navigator.of(ctx).maybePop(); // 关闭已显示的弹窗

    showDialog(
      context: ctx,
      builder: (dialogCtx) => AlertDialog(
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogCtx),
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  /// GET 请求
  static Future<Map<String, dynamic>> get(String path, {Map<String, String>? headers}) async {
    final resp = await http.get(
      Uri.parse('${ApiConfig.baseUrl}$path'),
      headers: {
        'Content-Type': 'application/json',
        if (headers != null) ...headers,
      },
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    try {
      final data = json.decode(resp.body) as Map<String, dynamic>;
      _checkError(data, resp.statusCode);
      return data;
    } catch (e) {
      if (e is ApiException) rethrow;
      // JSON 解析失败或网络错误，转为 ApiException
      _showErrorDialog('请求失败: $e');
      throw ApiException('请求失败: $e');
    }
  }

  /// POST 请求
  static Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
  }) async {
    final resp = await http.post(
      Uri.parse('${ApiConfig.baseUrl}$path'),
      headers: {
        'Content-Type': 'application/json',
        if (headers != null) ...headers,
      },
      body: body != null ? json.encode(body) : null,
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    try {
      final data = json.decode(resp.body) as Map<String, dynamic>;
      _checkError(data, resp.statusCode);
      return data;
    } catch (e) {
      if (e is ApiException) rethrow;
      _showErrorDialog('请求失败: $e');
      throw ApiException('请求失败: $e');
    }
  }

  /// PUT 请求
  static Future<Map<String, dynamic>> put(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
  }) async {
    final resp = await http.put(
      Uri.parse('${ApiConfig.baseUrl}$path'),
      headers: {
        'Content-Type': 'application/json',
        if (headers != null) ...headers,
      },
      body: body != null ? json.encode(body) : null,
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    try {
      final data = json.decode(resp.body) as Map<String, dynamic>;
      _checkError(data, resp.statusCode);
      return data;
    } catch (e) {
      if (e is ApiException) rethrow;
      _showErrorDialog('请求失败: $e');
      throw ApiException('请求失败: $e');
    }
  }

  /// DELETE 请求
  static Future<Map<String, dynamic>> delete(
    String path, {
    Map<String, String>? headers,
  }) async {
    final resp = await http.delete(
      Uri.parse('${ApiConfig.baseUrl}$path'),
      headers: {
        'Content-Type': 'application/json',
        if (headers != null) ...headers,
      },
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    try {
      final data = json.decode(resp.body) as Map<String, dynamic>;
      _checkError(data, resp.statusCode);
      return data;
    } catch (e) {
      if (e is ApiException) rethrow;
      _showErrorDialog('请求失败: $e');
      throw ApiException('请求失败: $e');
    }
  }
}