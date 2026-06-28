import 'token_manager.dart';
import '../../core/utils/api_client.dart';

class CommentRepository {
  Future<Map<String, String>> _headers() async {
    final token = await TokenManager.getToken();
    final h = <String, String>{};
    if (token != null) h['Authorization'] = 'Bearer $token';
    return h;
  }

  Future<List<Map<String, dynamic>>> getComments(int newsId) async {
    final data = await ApiClient.get(
      '/api/comments/$newsId',
      headers: await _headers(),
    );
    return List<Map<String, dynamic>>.from(data['comments'] ?? []);
  }

  Future<void> addComment(int newsId, String content) async {
    await ApiClient.post(
      '/api/comments',
      body: {'news_id': newsId, 'content': content},
      headers: await _headers(),
    );
  }

  Future<void> updateComment(int commentId, String content) async {
    await ApiClient.put(
      '/api/comments/$commentId',
      body: {'content': content},
      headers: await _headers(),
    );
  }

  Future<void> deleteComment(int commentId) async {
    await ApiClient.delete(
      '/api/comments/$commentId',
      headers: await _headers(),
    );
  }
}