import 'package:http/http.dart' as http;
import 'dart:convert';
import 'token_manager.dart';

class ConfigRepository {
  static const String _baseUrl = 'http://localhost:3000';

  Future<Map<String, dynamic>> getConfig() async {
    final resp = await http.get(
      Uri.parse('$_baseUrl/api/config'),
    ).timeout(const Duration(seconds: 10));

    return json.decode(resp.body);
  }
}