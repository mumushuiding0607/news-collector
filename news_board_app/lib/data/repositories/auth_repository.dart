import 'token_manager.dart';
import '../../core/utils/api_client.dart';

class AuthRepository {
  Future<Map<String, dynamic>> sendCode(String email) async {
    final data = await ApiClient.post(
      '/api/auth/send_code',
      body: {'email': email},
    );
    return {'success': true, 'code': data['code']};
  }

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String code,
  }) async {
    final data = await ApiClient.post(
      '/api/auth/email_register',
      body: {'email': email, 'password': password, 'code': code},
    );
    await TokenManager.setToken(data['token']);
    return data;
  }

  Future<Map<String, dynamic>> loginWithCode(String phone, String code) async {
    final data = await ApiClient.post(
      '/api/auth/login_code',
      body: {'phone': phone, 'code': code},
    );
    await TokenManager.setToken(data['token']);
    return data;
  }

  Future<Map<String, dynamic>> loginWithPassword(String email, String password) async {
    final data = await ApiClient.post(
      '/api/auth/login_password',
      body: {'email': email, 'password': password},
    );
    await TokenManager.setToken(data['token']);
    return data;
  }

  Future<Map<String, dynamic>> getCurrentUser() async {
    final token = await TokenManager.getToken();
    final headers = <String, String>{};
    if (token != null) headers['Authorization'] = 'Bearer $token';
    return ApiClient.get('/api/auth/current_user', headers: headers);
  }

  Future<void> logout() async {
    final token = await TokenManager.getToken();
    if (token == null) return;
    try {
      await ApiClient.post(
        '/api/auth/logout',
        headers: {'Authorization': 'Bearer $token'},
      );
    } finally {
      await TokenManager.clear();
    }
  }

  Future<void> sendResetCode(String email) async {
    await ApiClient.post(
      '/api/auth/send_reset_code',
      body: {'email': email},
    );
  }

  Future<void> resetPassword(String email, String code, String newPassword) async {
    await ApiClient.post(
      '/api/auth/reset_password',
      body: {'email': email, 'code': code, 'new_password': newPassword},
    );
  }

  Future<Map<String, dynamic>> getUserInfo() async {
    final token = await TokenManager.getToken();
    final headers = <String, String>{};
    if (token != null) headers['Authorization'] = 'Bearer $token';
    return ApiClient.get('/api/auth/user_info', headers: headers);
  }

  Future<void> updateNickname(String nickname) async {
    final token = await TokenManager.getToken();
    await ApiClient.put(
      '/api/auth/update_nickname',
      body: {'nickname': nickname},
      headers: token != null ? {'Authorization': 'Bearer $token'} : {},
    );
  }

  Future<void> updatePhone(String phone, String code) async {
    final token = await TokenManager.getToken();
    await ApiClient.put(
      '/api/auth/update_phone',
      body: {'phone': phone, 'code': code},
      headers: token != null ? {'Authorization': 'Bearer $token'} : {},
    );
  }

  Future<void> updateEmail(String email, String code) async {
    final token = await TokenManager.getToken();
    await ApiClient.put(
      '/api/auth/update_email',
      body: {'email': email, 'code': code},
      headers: token != null ? {'Authorization': 'Bearer $token'} : {},
    );
  }

  Future<void> updatePassword(String oldPassword, String newPassword) async {
    final token = await TokenManager.getToken();
    await ApiClient.put(
      '/api/auth/update_password',
      body: {'old_password': oldPassword, 'new_password': newPassword},
      headers: token != null ? {'Authorization': 'Bearer $token'} : {},
    );
  }
}