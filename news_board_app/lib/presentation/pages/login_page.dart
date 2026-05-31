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
  final _phoneController = TextEditingController();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _codeSent = false;
  int _countdown = 0;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _initTabController();
  }

  void _initTabController() {
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
    _phoneController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _sendCode() async {
    if (_phoneController.text.length != 11) {
      _showError('请输入正确的手机号');
      return;
    }
    setState(() => _isLoading = true);
    final ok = await ref.read(authProvider.notifier).sendCode(_phoneController.text);
    setState(() => _isLoading = false);
    if (ok && mounted) {
      setState(() {
        _codeSent = true;
        _countdown = 60;
      });
      _startCountdown();
    } else {
      _showError('发送失败，请稍后重试');
    }
  }

  void _startCountdown() {
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 1));
      if (mounted) {
        setState(() => _countdown--);
        return _countdown > 0;
      }
      return false;
    });
  }

  void _login() async {
    if (_phoneController.text.length != 11) {
      _showError('请输入正确的手机号');
      return;
    }
    if (_tabController.index == 0 && !_codeSent) {
      _showError('请先获取验证码');
      return;
    }
    if (_tabController.index == 0 && _codeController.text.isEmpty) {
      _showError('请输入验证码');
      return;
    }
    if (_tabController.index == 1 && _passwordController.text.isEmpty) {
      _showError('请输入密码');
      return;
    }

    setState(() => _isLoading = true);

    bool ok = false;
    if (_tabController.index == 0) {
      ok = await ref.read(authProvider.notifier).loginWithCode(
        _phoneController.text,
        _codeController.text,
      );
    } else {
      ok = await ref.read(authProvider.notifier).loginWithPassword(
        _phoneController.text,
        _passwordController.text,
      );
    }

    setState(() => _isLoading = false);

    if (ok && mounted) {
      context.go('/');
    } else {
      final err = ref.read(authProvider).errorMessage ?? '登录失败';
      _showError(err);
    }
  }

  void _showError(String msg) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg), backgroundColor: Colors.red),
      );
    }
  }

  void _showForgotPasswordDialog() {
    final emailController = TextEditingController();
    final codeController = TextEditingController();
    final newPwdController = TextEditingController();
    String step = 'email'; // 'email' | 'code' | 'done'
    int countdown = 0;

    showDialog(
      context: context,
      barrierColor: Colors.black87,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            backgroundColor: const Color(0xFF2A2A2A),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Text('找回密码', style: TextStyle(color: Colors.white)),
            content: step == 'done'
                ? const Text('密码重置成功，请返回登录', style: TextStyle(color: Colors.white70))
                : Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (step == 'email') ...[
                        TextField(
                          controller: emailController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: '请输入注册邮箱',
                            hintStyle: const TextStyle(color: Colors.white30),
                            filled: true,
                            fillColor: Colors.white.withOpacity(0.08),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: countdown > 0
                                ? null
                                : () async {
                                    final ok = await ref.read(authProvider.notifier).sendResetCode(emailController.text);
                                    if (ok && ctx.mounted) {
                                      setDialogState(() {
                                        step = 'code';
                                        countdown = 60;
                                      });
                                      _startDialogCountdown(ctx, setDialogState, () => countdown, (v) => countdown = v);
                                    }
                                  },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.amber.shade700,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                            child: Text(countdown > 0 ? '${countdown}s' : '发送验证码'),
                          ),
                        ),
                      ],
                      if (step == 'code') ...[
                        TextField(
                          controller: codeController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: '输入验证码',
                            hintStyle: const TextStyle(color: Colors.white30),
                            filled: true,
                            fillColor: Colors.white.withOpacity(0.08),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: newPwdController,
                          obscureText: true,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: '输入新密码（至少6位）',
                            hintStyle: const TextStyle(color: Colors.white30),
                            filled: true,
                            fillColor: Colors.white.withOpacity(0.08),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: () async {
                              if (newPwdController.text.length < 6) return;
                              final ok = await ref.read(authProvider.notifier).resetPassword(
                                emailController.text,
                                codeController.text,
                                newPwdController.text,
                              );
                              if (ok && ctx.mounted) {
                                setDialogState(() => step = 'done');
                              }
                            },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.amber.shade700,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                            child: const Text('重置密码'),
                          ),
                        ),
                      ],
                    ],
                  ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('取消', style: TextStyle(color: Colors.white54)),
              ),
            ],
          );
        },
      ),
    );
  }

  void _startDialogCountdown(BuildContext ctx, StateSetter setState, int Function() get, void Function(int) set) {
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 1));
      if (ctx.mounted) {
        setState(() => set(get() - 1));
        return get() > 0;
      }
      return false;
    });
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
                Expanded(child: _buildTabContent(config)),
              ] else ...[
                const SizedBox(height: 24),
                Expanded(child: _buildSingleTabContent(config)),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabBar(AppConfig config) {
    final tabs = <Widget>[];
    if (config.smsLoginEnabled) tabs.add(const Tab(text: '验证码登录'));
    if (config.passwordLoginEnabled) tabs.add(const Tab(text: '密码登录'));

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 40),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      child: TabBar(
        controller: _tabController,
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
    final children = <Widget>[];
    if (config.smsLoginEnabled) children.add(_buildCodeLogin());
    if (config.passwordLoginEnabled) children.add(_buildPasswordLogin());

    return TabBarView(
      controller: _tabController,
      children: children,
    );
  }

  Widget _buildSingleTabContent(AppConfig config) {
    if (config.smsLoginEnabled && !config.passwordLoginEnabled) {
      return _buildCodeLogin();
    }
    return _buildPasswordLogin();
  }

  Widget _buildCodeLogin() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        children: [
          LoginTextField(
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            icon: Icons.phone_android,
            hintText: '请输入手机号',
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: LoginTextField(
                  controller: _codeController,
                  keyboardType: TextInputType.number,
                  icon: Icons.lock_outline,
                  hintText: '请输入验证码',
                ),
              ),
              const SizedBox(width: 12),
              SendCodeButton(
                codeSent: _codeSent,
                countdown: _countdown,
                onPressed: _isLoading ? null : _sendCode,
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

  Widget _buildPasswordLogin() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        children: [
          LoginTextField(
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            icon: Icons.phone_android,
            hintText: '请输入手机号',
          ),
          const SizedBox(height: 16),
          LoginTextField(
            controller: _passwordController,
            keyboardType: TextInputType.visiblePassword,
            icon: Icons.lock,
            hintText: '请输入密码',
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
              child: const Text(
                '忘记密码？',
                style: TextStyle(color: Colors.white38, fontSize: 13),
              ),
            ),
          ),
          TextButton(
            onPressed: () => context.go('/register'),
            child: const Text(
              '没有账号？去注册',
              style: TextStyle(color: Colors.white54, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }
}
