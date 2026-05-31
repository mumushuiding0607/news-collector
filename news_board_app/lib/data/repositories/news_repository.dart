import 'package:http/http.dart' as http;
import 'dart:convert';
import '../models/news_item.dart';
import 'token_manager.dart';

class NewsRepository {
  static const String _baseUrl = 'http://localhost:3000';

  Map<String, String> get _headers {
    final token = TokenManager.getToken();
    final h = <String, String>{'Content-Type': 'application/json'};
    if (token != null) h['Authorization'] = 'Bearer $token';
    return h;
  }

  Future<List<NewsItem>> fetchHotNews() async {
    return _fetchNews('/api/news/hot');
  }

  Future<List<NewsItem>> fetchLatestNews() async {
    return _fetchNews('/api/news/latest');
  }

  Future<List<NewsItem>> fetchHistoryNews() async {
    return _fetchNews('/api/news/history');
  }

  Future<List<NewsItem>> _fetchNews(String endpoint) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl$endpoint'),
        headers: _headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final List<dynamic> newsList = data['data'] ?? [];
        return newsList.map((json) => NewsItem.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load news: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to connect to news API: $e');
    }
  }
}