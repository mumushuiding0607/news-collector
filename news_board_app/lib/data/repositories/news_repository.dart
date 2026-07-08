import '../models/news_item.dart';
import 'token_manager.dart';
import '../../core/utils/api_client.dart';

class NewsRepository {
  Future<Map<String, List<NewsItem>>> fetchAllNews() async {
    final token = await TokenManager.getToken();
    final headers = <String, String>{};
    if (token != null) headers['Authorization'] = 'Bearer $token';

    final data = await ApiClient.get('/api/news/all', headers: headers);

    return {
      'latest': (data['latest']['data'] as List<dynamic>? ?? [])
          .map((e) => NewsItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      'hot': (data['hot']['data'] as List<dynamic>? ?? [])
          .map((e) => NewsItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      'history': (data['history']['data'] as List<dynamic>? ?? [])
          .map((e) => NewsItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    };
  }

  Future<Map<String, List<AiNewsItem>>> fetchAllAiNews() async {
    final token = await TokenManager.getToken();
    final headers = <String, String>{};
    if (token != null) headers['Authorization'] = 'Bearer $token';

    final data = await ApiClient.get('/api/news/ai/all', headers: headers);

    return {
      'latest': (data['latest']['data'] as List<dynamic>? ?? [])
          .map((e) => AiNewsItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      'history': (data['history']['data'] as List<dynamic>? ?? [])
          .map((e) => AiNewsItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      'hot': [], // AI 新闻暂无 hot
    };
  }
}