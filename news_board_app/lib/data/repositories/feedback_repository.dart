import 'token_manager.dart';
import '../../core/utils/api_client.dart';

class FeedbackRepository {
  Future<void> submit({
    required String content,
    String type = 'suggestion',
  }) async {
    final token = await TokenManager.getToken();
    final headers = <String, String>{};
    if (token != null) headers['Authorization'] = 'Bearer $token';

    await ApiClient.post(
      '/api/feedback',
      body: {'content': content, 'type': type},
      headers: headers,
    );
  }
}