import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../core/providers/config_provider.dart';

class ConfigRepository {
  Future<Map<String, dynamic>> getConfig() async {
    // 使用公开端点，无需认证即可获取前端配置（锁定规则、UI文本等）
    final resp = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/config/public'),
    ).timeout(Duration(seconds: ApiConfig.defaultTimeout));

    return json.decode(resp.body);
  }
}