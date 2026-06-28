import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/config_provider.dart';
import '../../data/repositories/auth_repository.dart';

class AccountPage extends ConsumerStatefulWidget {
  const AccountPage({super.key});

  @override
  ConsumerState<AccountPage> createState() => _AccountPageState();
}

class _AccountPageState extends ConsumerState<AccountPage> {
  // 昵称编辑
  final _nicknameController = TextEditingController();
  bool _isEditingNickname = false;
  bool _isLoadingNickname = false;

  // 手机号修改
  final _phoneController = TextEditingController();
  final _phoneCodeController = TextEditingController();
  bool _isEditingPhone = false;
  bool _isLoadingPhone = false;
  bool _phoneCodeSent = false;
  int _phoneCountdown = 0;

  // 邮箱修改
  final _emailController = TextEditingController();
  final _emailCodeController = TextEditingController();
  bool _isEditingEmail = false;
  bool _isLoadingEmail = false;
  bool _emailCodeSent = false;
  int _emailCountdown = 0;

  // 密码修改
  final _oldPwdController = TextEditingController();
  final _newPwdController = TextEditingController();
  final _confirmPwdController = TextEditingController();
  bool _isEditingPassword = false;
  bool _isLoadingPassword = false;

  // 取消标记，用于停止 countdown
  bool _disposed = false;

  @override
  void dispose() {
    _disposed = true;
    _nicknameController.dispose();
    _phoneController.dispose();
    _phoneCodeController.dispose();
    _emailController.dispose();
    _emailCodeController.dispose();
    _oldPwdController.dispose();
    _newPwdController.dispose();
    _confirmPwdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final config = ref.watch(configProvider);
    final user = authState.currentUser;

    // auth 加载完成后，填充控制器
    if (user != null) {
      if (_nicknameController.text.isEmpty && user.nickname != null) {
        _nicknameController.text = user.nickname!;
      }
      if (_phoneController.text.isEmpty && user.phone != null) {
        _phoneController.text = user.phone!;
      }
      if (_emailController.text.isEmpty && user.email != null) {
        _emailController.text = user.email!;
      }
    }

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0D0D0D), Color(0xFF121212)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(context),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildUserInfoCard(user, config.features.subscriptionEnabled),
                      const SizedBox(height: 24),
                      _buildNicknameSection(),
                      const SizedBox(height: 24),
                      _buildPhoneSection(),
                      const SizedBox(height: 24),
                      _buildEmailSection(),
                      const SizedBox(height: 24),
                      _buildPasswordSection(),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          IconButton(
            onPressed: () => context.go('/'),
            icon: const Icon(Icons.arrow_back, color: Colors.white),
          ),
          const Expanded(
            child: Text(
              '账号管理',
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(width: 48),
        ],
      ),
    );
  }

  Widget _buildUserInfoCard(User? user, bool subscriptionEnabled) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Colors.amber.withOpacity(0.15), Colors.amber.withOpacity(0.05)],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.amber.withOpacity(0.3)),
      ),
      child: Row(
        children: [
                            CircleAvatar(
            radius: 30,
            backgroundColor: Colors.amber.shade700,
            child: Text(
              (user?.nickname ?? user?.email ?? '用户').length > 0
                  ? (user?.nickname ?? user?.email ?? '用户').substring(0, 1).toUpperCase()
                  : '用',
              style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user?.nickname ?? '未设置昵称',
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
                if (subscriptionEnabled) ...[
                  const SizedBox(height: 4),
                  Text(
                    _getSubscriptionText(user?.subscriptionLevel ?? 'free'),
                    style: TextStyle(color: Colors.amber.shade400, fontSize: 14),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _getSubscriptionText(String level) {
    switch (level) {
      case 'pro':
        return 'Pro 会员';
      case 'premium':
        return 'Premium 会员';
      default:
        return '免费用户';
    }
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        title,
        style: const TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildNicknameSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle('昵称'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Expanded(
                child: _isEditingNickname
                    ? TextField(
                        controller: _nicknameController,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          hintText: '请输入昵称',
                          hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
                          border: InputBorder.none,
                          isDense: true,
                          contentPadding: EdgeInsets.zero,
                        ),
                      )
                    : Text(
                        ref.read(authProvider).currentUser?.nickname ?? '未设置',
                        style: const TextStyle(color: Colors.white, fontSize: 16),
                      ),
              ),
              if (_isEditingNickname) ...[
                const SizedBox(width: 8),
                if (_isLoadingNickname)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.amber),
                  )
                else
                  IconButton(
                    onPressed: _saveNickname,
                    icon: const Icon(Icons.check, color: Colors.amber),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                const SizedBox(width: 8),
                IconButton(
                  onPressed: () => setState(() => _isEditingNickname = false),
                  icon: const Icon(Icons.close, color: Colors.white54),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ] else
                IconButton(
                  onPressed: () => setState(() => _isEditingNickname = true),
                  icon: const Icon(Icons.edit, color: Colors.white54),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPhoneSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle('手机号'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Row(
                children: [
                  const Text('手机号', style: TextStyle(color: Colors.white54, fontSize: 14)),
                  const SizedBox(width: 16),
                  Expanded(
                    child: _isEditingPhone
                        ? TextField(
                            controller: _phoneController,
                            keyboardType: TextInputType.phone,
                            style: const TextStyle(color: Colors.white),
                            decoration: InputDecoration(
                              hintText: '请输入新手机号',
                              hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
                              border: InputBorder.none,
                              isDense: true,
                              contentPadding: EdgeInsets.zero,
                            ),
                          )
                        : Text(
                            ref.read(authProvider).currentUser?.phone ?? '未绑定',
                            style: const TextStyle(color: Colors.white, fontSize: 16),
                          ),
                  ),
                ],
              ),
              if (_isEditingPhone) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _phoneCodeController,
                        keyboardType: TextInputType.number,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          hintText: '验证码',
                          hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: BorderSide(color: Colors.white.withOpacity(0.2)),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: BorderSide(color: Colors.white.withOpacity(0.2)),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(color: Colors.amber),
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    _buildSendPhoneCodeButton(),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _isLoadingPhone ? null : _savePhone,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.amber.shade700,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        child: _isLoadingPhone
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                              )
                            : const Text('确认修改', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                      ),
                    ),
                    const SizedBox(width: 12),
                    TextButton(
                      onPressed: () => setState(() {
                        _isEditingPhone = false;
                        _phoneCodeSent = false;
                        _phoneCountdown = 0;
                        _phoneCodeController.clear();
                      }),
                      child: const Text('取消', style: TextStyle(color: Colors.white54)),
                    ),
                  ],
                ),
              ] else
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () => setState(() => _isEditingPhone = true),
                    child: const Text('修改', style: TextStyle(color: Colors.amber)),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSendPhoneCodeButton() {
    return OutlinedButton(
      onPressed: _phoneCountdown > 0 ? null : () => _sendPhoneCode(),
      style: OutlinedButton.styleFrom(
        side: BorderSide(color: Colors.amber.withOpacity(0.5)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      child: Text(
        _phoneCountdown > 0 ? '${_phoneCountdown}s' : '发送验证码',
        style: TextStyle(color: _phoneCountdown > 0 ? Colors.white54 : Colors.amber, fontSize: 12),
      ),
    );
  }

  Widget _buildEmailSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle('邮箱'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Row(
                children: [
                  const Text('邮箱', style: TextStyle(color: Colors.white54, fontSize: 14)),
                  const SizedBox(width: 16),
                  Expanded(
                    child: _isEditingEmail
                        ? TextField(
                            controller: _emailController,
                            keyboardType: TextInputType.emailAddress,
                            style: const TextStyle(color: Colors.white),
                            decoration: InputDecoration(
                              hintText: '请输入新邮箱',
                              hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
                              border: InputBorder.none,
                              isDense: true,
                              contentPadding: EdgeInsets.zero,
                            ),
                          )
                        : Text(
                            ref.read(authProvider).currentUser?.email ?? '未绑定',
                            style: const TextStyle(color: Colors.white, fontSize: 16),
                          ),
                  ),
                ],
              ),
              if (_isEditingEmail) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _emailCodeController,
                        keyboardType: TextInputType.number,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          hintText: '验证码',
                          hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: BorderSide(color: Colors.white.withOpacity(0.2)),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: BorderSide(color: Colors.white.withOpacity(0.2)),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(color: Colors.amber),
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    _buildSendEmailCodeButton(),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _isLoadingEmail ? null : _saveEmail,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.amber.shade700,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        child: _isLoadingEmail
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                              )
                            : const Text('确认修改', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                      ),
                    ),
                    const SizedBox(width: 12),
                    TextButton(
                      onPressed: () => setState(() {
                        _isEditingEmail = false;
                        _emailCodeSent = false;
                        _emailCountdown = 0;
                        _emailCodeController.clear();
                      }),
                      child: const Text('取消', style: TextStyle(color: Colors.white54)),
                    ),
                  ],
                ),
              ] else
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () => setState(() => _isEditingEmail = true),
                    child: const Text('修改', style: TextStyle(color: Colors.amber)),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSendEmailCodeButton() {
    return OutlinedButton(
      onPressed: _emailCountdown > 0 ? null : () => _sendEmailCode(),
      style: OutlinedButton.styleFrom(
        side: BorderSide(color: Colors.amber.withOpacity(0.5)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      child: Text(
        _emailCountdown > 0 ? '${_emailCountdown}s' : '发送验证码',
        style: TextStyle(color: _emailCountdown > 0 ? Colors.white54 : Colors.amber, fontSize: 12),
      ),
    );
  }

  Widget _buildPasswordSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle('修改密码'),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              if (_isEditingPassword) ...[
                _buildPasswordField(_oldPwdController, '旧密码', true),
                const SizedBox(height: 12),
                _buildPasswordField(_newPwdController, '新密码（至少6位）', true),
                const SizedBox(height: 12),
                _buildPasswordField(_confirmPwdController, '确认新密码', true),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _isLoadingPassword ? null : _savePassword,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.amber.shade700,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        child: _isLoadingPassword
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                              )
                            : const Text('确认修改', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                      ),
                    ),
                    const SizedBox(width: 12),
                    TextButton(
                      onPressed: () => setState(() {
                        _isEditingPassword = false;
                        _oldPwdController.clear();
                        _newPwdController.clear();
                        _confirmPwdController.clear();
                      }),
                      child: const Text('取消', style: TextStyle(color: Colors.white54)),
                    ),
                  ],
                ),
              ] else
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('密码', style: TextStyle(color: Colors.white54, fontSize: 14)),
                    TextButton(
                      onPressed: () => setState(() => _isEditingPassword = true),
                      child: const Text('修改', style: TextStyle(color: Colors.amber)),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPasswordField(TextEditingController controller, String hint, bool obscure) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.2)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.2)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Colors.amber),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      ),
    );
  }

  // ============ 业务逻辑 ============

  Future<void> _saveNickname() async {
    final nickname = _nicknameController.text.trim();
    if (nickname.isEmpty) {
      _showError('请输入昵称');
      return;
    }
    setState(() => _isLoadingNickname = true);
    final ok = await ref.read(authProvider.notifier).updateNickname(nickname);
    setState(() => _isLoadingNickname = false);
    if (ok) {
      setState(() => _isEditingNickname = false);
      _showSuccess('昵称已更新');
    } else {
      _showError(ref.read(authProvider).errorMessage ?? '更新失败');
    }
  }

  Future<void> _sendPhoneCode() async {
    final phone = _phoneController.text.trim();
    if (!RegExp(r'^1[3-9]\d{9}$').hasMatch(phone)) {
      _showError('请输入正确的手机号');
      return;
    }
    await AuthRepository().sendCode(phone);
    setState(() {
      _phoneCodeSent = true;
      _phoneCountdown = 60;
    });
    _startPhoneCountdown();
    _showSuccess('验证码已发送');
  }

  void _startPhoneCountdown() {
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 1));
      if (_disposed) return false;
      if (!mounted) return false;
      setState(() {
        if (_phoneCountdown > 0) _phoneCountdown--;
      });
      return _phoneCountdown > 0;
    });
  }

  Future<void> _savePhone() async {
    final phone = _phoneController.text.trim();
    final code = _phoneCodeController.text.trim();
    if (!RegExp(r'^1[3-9]\d{9}$').hasMatch(phone)) {
      _showError('请输入正确的手机号');
      return;
    }
    if (code.isEmpty) {
      _showError('请输入验证码');
      return;
    }
    setState(() => _isLoadingPhone = true);
    final ok = await ref.read(authProvider.notifier).updatePhone(phone, code);
    setState(() => _isLoadingPhone = false);
    if (ok) {
      setState(() {
        _isEditingPhone = false;
        _phoneCodeSent = false;
        _phoneCountdown = 0;
        _phoneCodeController.clear();
      });
      _showSuccess('手机号已更新');
    } else {
      _showError(ref.read(authProvider).errorMessage ?? '更新失败');
    }
  }

  Future<void> _sendEmailCode() async {
    final email = _emailController.text.trim();
    if (!RegExp(r'^[\w\.-]+@[\w\.-]+\.\w+$').hasMatch(email)) {
      _showError('请输入正确的邮箱');
      return;
    }
    await AuthRepository().sendCode(email);
    setState(() {
      _emailCodeSent = true;
      _emailCountdown = 60;
    });
    _startEmailCountdown();
    _showSuccess('验证码已发送');
  }

  void _startEmailCountdown() {
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 1));
      if (_disposed) return false;
      if (!mounted) return false;
      setState(() {
        if (_emailCountdown > 0) _emailCountdown--;
      });
      return _emailCountdown > 0;
    });
  }

  Future<void> _saveEmail() async {
    final email = _emailController.text.trim();
    final code = _emailCodeController.text.trim();
    if (!RegExp(r'^[\w\.-]+@[\w\.-]+\.\w+$').hasMatch(email)) {
      _showError('请输入正确的邮箱');
      return;
    }
    if (code.isEmpty) {
      _showError('请输入验证码');
      return;
    }
    setState(() => _isLoadingEmail = true);
    final ok = await ref.read(authProvider.notifier).updateEmail(email, code);
    setState(() => _isLoadingEmail = false);
    if (ok) {
      setState(() {
        _isEditingEmail = false;
        _emailCodeSent = false;
        _emailCountdown = 0;
        _emailCodeController.clear();
      });
      _showSuccess('邮箱已更新');
    } else {
      _showError(ref.read(authProvider).errorMessage ?? '更新失败');
    }
  }

  Future<void> _savePassword() async {
    final oldPwd = _oldPwdController.text;
    final newPwd = _newPwdController.text;
    final confirmPwd = _confirmPwdController.text;
    if (oldPwd.isEmpty) {
      _showError('请输入旧密码');
      return;
    }
    if (newPwd.length < 6) {
      _showError('新密码至少6位');
      return;
    }
    if (newPwd != confirmPwd) {
      _showError('两次输入的密码不一致');
      return;
    }
    setState(() => _isLoadingPassword = true);
    final ok = await ref.read(authProvider.notifier).updatePassword(oldPwd, newPwd);
    setState(() => _isLoadingPassword = false);
    if (ok) {
      setState(() {
        _isEditingPassword = false;
        _oldPwdController.clear();
        _newPwdController.clear();
        _confirmPwdController.clear();
      });
      _showSuccess('密码已更新');
    } else {
      _showError(ref.read(authProvider).errorMessage ?? '更新失败');
    }
  }

  void _showError(String msg) {
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(msg),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('确定')),
        ],
      ),
    );
  }

  void _showSuccess(String msg) {
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(msg),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('确定')),
        ],
      ),
    );
  }
}