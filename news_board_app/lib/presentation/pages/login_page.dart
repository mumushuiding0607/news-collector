import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/config_provider.dart';
import '../widgets/login_header.dart';
import '../widgets/login_form.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _codeSent = false;
  int _countdown = 0;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    final config = ref.read(configProvider);
    _tabController = TabController(length: _calcTabCount(config), vsync: this);
  }

  int _calcTabCount(AppConfig config) {
    int count = 0;
    if (config.smsLoginEnabled) count++;
    if (config.passwordLoginEnabled) count++;
    return count.clamp(1, 2);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _emailController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _sendCode() async {
    if (_emailController.text.isEmpty || !_emailController.text.contains('@')) {
      _showError('请输入正确的邮箱');
      return;
    }
    setState(() => _isLoading = true);
    final ok = await ref.read(authProvider.notifier).sendCode(_emailController.text);
    if (mounted) {
      setState(() => _isLoading = false);
      if (ok) {
        setState(() {
          _codeSent = true;
          _countdown = 60;
        });
        _startCountdown();
      }
    }
  }

  void _startCountdown() {
    Future.delayed(const Duration(seconds: 1), () {
      if (!mounted) return;
      setState(() => _countdown--);
      if (_countdown > 0) {
        _startCountdown();
      }
    });
  }

  Future<void> _login() async {
    // 判断是哪个tab：smsLoginEnabled时index=0为验证码登录，index=1为密码登录
    final config = ref.read(configProvider);
    final smsEnabled = config.smsLoginEnabled;
    final pwdEnabled = config.passwordLoginEnabled;

    bool isCodeLogin = false;
    bool isPasswordLogin = false;

    if (smsEnabled && pwdEnabled) {
      // 双tab：0=验证码登录，1=密码登录
      isCodeLogin = _tabController.index == 0;
      isPasswordLogin = _tabController.index == 1;
    } else if (smsEnabled) {
      // 只有验证码登录
      isCodeLogin = true;
    } else {
      // 只有密码登录
      isPasswordLogin = true;
    }

    if (isCodeLogin) {
      if (!_codeSent) {
        _showError('请先获取验证码');
        return;
      }
      if (_codeController.text.isEmpty) {
        _showError('请输入验证码');
        return;
      }
    }

    if (isPasswordLogin) {
      if (_emailController.text.isEmpty || !_emailController.text.contains('@')) {
        _showError('请输入正确的邮箱');
        return;
      }
      if (_passwordController.text.isEmpty) {
        _showError('请输入密码');
        return;
      }
    }

    setState(() => _isLoading = true);

    bool ok = false;
    if (isCodeLogin) {
      ok = await ref.read(authProvider.notifier).loginWithCode(
        _emailController.text,
        _codeController.text,
      );
    } else {
      ok = await ref.read(authProvider.notifier).loginWithPassword(
        _emailController.text,
        _passwordController.text,
      );
    }

    if (!mounted) return;

    setState(() => _isLoading = false);

    if (ok) {
      context.go('/');
    }
    // 错误已由 ApiClient 弹窗提示
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

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(configProvider);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0D0D0D), Color(0xFF1A1A1A)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 60),
              const LoginHeader(),
              const SizedBox(height: 40),
              if (_calcTabCount(config) > 1) ...[
                _buildTabBar(config),
                const SizedBox(height: 24),
                Expanded(child: SingleChildScrollView(child: _buildTabContent(config))),
              ] else ...[
                const SizedBox(height: 24),
                Expanded(child: SingleChildScrollView(child: _buildSingleTabContent(config))),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabBar(AppConfig config) {
    final uiTexts = config.uiTexts.login;
    final tabs = <Widget>[];
    if (config.smsLoginEnabled) tabs.add(Tab(text: uiTexts.tabCode));
    if (config.passwordLoginEnabled) tabs.add(Tab(text: uiTexts.tabPassword));

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 40),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      child: TabBar(
        controller: _tabController,
        indicatorSize: TabBarIndicatorSize.tab,
        indicator: BoxDecoration(
          color: Colors.white.withOpacity(0.15),
          borderRadius: BorderRadius.circular(10),
        ),
        labelColor: Colors.white,
        unselectedLabelColor: Colors.white54,
        tabs: tabs,
      ),
    );
  }

  Widget _buildTabContent(AppConfig config) {
    final uiTexts = config.uiTexts.login;
    final children = <Widget>[];
    if (config.smsLoginEnabled) children.add(_buildCodeLogin(uiTexts));
    if (config.passwordLoginEnabled) children.add(_buildPasswordLogin(uiTexts));

    return TabBarView(
      controller: _tabController,
      children: children,
    );
  }

  Widget _buildSingleTabContent(AppConfig config) {
    final uiTexts = config.uiTexts.login;
    if (config.smsLoginEnabled && !config.passwordLoginEnabled) {
      return _buildCodeLogin(uiTexts);
    }
    return _buildPasswordLogin(uiTexts);
  }

  Widget _buildCodeLogin(UiTextsLogin uiTexts) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        children: [
          LoginTextField(
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            icon: Icons.email_outlined,
            hintText: uiTexts.hintEmail,
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: LoginTextField(
                  controller: _codeController,
                  keyboardType: TextInputType.number,
                  icon: Icons.lock_outline,
                  hintText: uiTexts.hintCode,
                ),
              ),
              const SizedBox(width: 12),
              SendCodeButton(
                codeSent: _codeSent,
                countdown: _countdown,
                onPressed: _isLoading ? null : _sendCode,
                isLoading: _isLoading,
              ),
            ],
          ),
          const SizedBox(height: 24),
          LoginButton(
            onPressed: _isLoading ? null : _login,
            isLoading: _isLoading,
          ),
        ],
      ),
    );
  }

  Widget _buildPasswordLogin(UiTextsLogin uiTexts) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        children: [
          LoginTextField(
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            icon: Icons.email_outlined,
            hintText: uiTexts.hintEmail,
          ),
          const SizedBox(height: 16),
          LoginTextField(
            controller: _passwordController,
            keyboardType: TextInputType.visiblePassword,
            icon: Icons.lock,
            hintText: uiTexts.hintPassword,
            obscureText: true,
          ),
          const SizedBox(height: 16),
          LoginButton(
            onPressed: _isLoading ? null : _login,
            isLoading: _isLoading,
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => _showForgotPasswordDialog(),
              child: Text(
                uiTexts.linkForgotPassword,
                style: const TextStyle(color: Colors.white38, fontSize: 13),
              ),
            ),
          ),
          TextButton(
            onPressed: () => context.go('/register'),
            child: Text(
              uiTexts.linkNoAccount,
              style: const TextStyle(color: Colors.white54, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  void _showForgotPasswordDialog() {
    showDialog(
      context: context,
      barrierColor: Colors.black87,
      builder: (ctx) => _ForgotPasswordDialog(email: _emailController.text),
    );
  }
}

class _ForgotPasswordDialog extends ConsumerStatefulWidget {
  final String email;

  const _ForgotPasswordDialog({required this.email});

  @override
  ConsumerState<_ForgotPasswordDialog> createState() => _ForgotPasswordDialogState();
}

class _ForgotPasswordDialogState extends ConsumerState<_ForgotPasswordDialog> {
  late TextEditingController _emailController;
  final _codeController = TextEditingController();
  final _newPwdController = TextEditingController();
  String _step = 'email';
  int _countdown = 0;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _emailController = TextEditingController(text: widget.email);
  }

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    _newPwdController.dispose();
    super.dispose();
  }

  void _startCountdown() {
    Future.delayed(const Duration(seconds: 1), () {
      if (!mounted) return;
      setState(() => _countdown--);
      if (_countdown > 0) {
        _startCountdown();
      }
    });
  }

  void _showErr(String msg) {
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

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF2A2A2A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: const Text('找回密码', style: TextStyle(color: Colors.white)),
      content: _step == 'done'
          ? const Text('密码重置成功，请返回登录', style: TextStyle(color: Colors.white70))
          : Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_step == 'email') ...[
                  TextField(
                    controller: _emailController,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: '请输入注册邮箱',
                      hintStyle: const TextStyle(color: Colors.white30),
                      filled: true,
                      fillColor: Colors.white.withOpacity(0.08),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: (_countdown > 0 || _isLoading) ? null : _sendResetCode,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.amber.shade700,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: _isLoading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                            )
                          : Text(_countdown > 0 ? '${_countdown}s' : '发送验证码'),
                    ),
                  ),
                ],
                if (_step == 'code') ...[
                  TextField(
                    controller: _codeController,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: '输入验证码',
                      hintStyle: const TextStyle(color: Colors.white30),
                      filled: true,
                      fillColor: Colors.white.withOpacity(0.08),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _newPwdController,
                    obscureText: true,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: '输入新密码（至少6位）',
                      hintStyle: const TextStyle(color: Colors.white30),
                      filled: true,
                      fillColor: Colors.white.withOpacity(0.08),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _resetPassword,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.amber.shade700,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: _isLoading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                            )
                          : const Text('重置密码'),
                    ),
                  ),
                ],
              ],
            ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('取消', style: TextStyle(color: Colors.white54)),
        ),
      ],
    );
  }

  Future<void> _sendResetCode() async {
    final email = _emailController.text.trim();
    if (!email.contains('@')) {
      _showErr('请输入正确的邮箱');
      return;
    }
    setState(() => _isLoading = true);
    final ok = await ref.read(authProvider.notifier).sendResetCode(email);
    if (mounted) {
      setState(() => _isLoading = false);
      if (ok) {
        setState(() {
          _step = 'code';
          _countdown = 60;
        });
        _startCountdown();
      }
    }
    // 错误已由 ApiClient 弹窗提示
  }

  Future<void> _resetPassword() async {
    final code = _codeController.text.trim();
    final newPwd = _newPwdController.text;
    if (code.isEmpty) {
      _showErr('请输入验证码');
      return;
    }
    if (newPwd.length < 6) {
      _showErr('密码至少6位');
      return;
    }
    setState(() => _isLoading = true);
    final ok = await ref.read(authProvider.notifier).resetPassword(
      _emailController.text.trim(),
      code,
      newPwd,
    );
    if (mounted) {
      setState(() => _isLoading = false);
      if (ok) {
        setState(() => _step = 'done');
      }
    }
    // 错误已由 ApiClient 弹窗提示
  }
}