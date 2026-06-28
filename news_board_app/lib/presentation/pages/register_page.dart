import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/auth_provider.dart';
import '../widgets/login_form.dart';

class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});

  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> {
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _isLoading = false;
  bool _codeSent = false;
  int _countdown = 0;

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  void _sendCode() async {
    if (!_emailController.text.contains('@')) {
      _showError('请输入正确的邮箱');
      return;
    }
    setState(() => _isLoading = true);
    final ok = await ref.read(authProvider.notifier).sendCode(_emailController.text);
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

  void _register() async {
    if (!_emailController.text.contains('@')) {
      _showError('请输入正确的邮箱');
      return;
    }
    if (!_codeSent || _codeController.text.isEmpty) {
      _showError('请先获取验证码');
      return;
    }
    if (_passwordController.text.length < 6) {
      _showError('密码至少6位');
      return;
    }
    if (_passwordController.text != _confirmController.text) {
      _showError('两次密码不一致');
      return;
    }

    setState(() => _isLoading = true);

    final ok = await ref.read(authProvider.notifier).register(
      _emailController.text,
      _passwordController.text,
      _codeController.text,
    );

    setState(() => _isLoading = false);

    if (ok && mounted) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          content: const Text('注册成功！'),
          actions: [
            TextButton(
              onPressed: () { Navigator.pop(ctx); context.go('/login'); },
              child: const Text('确定'),
            ),
          ],
        ),
      );
    } else {
      final err = ref.read(authProvider).errorMessage;
      _showError(err ?? '注册失败');
    }
  }

  void _showError(String msg) {
    if (mounted) {
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

  @override
  Widget build(BuildContext context) {
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
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40),
            child: Column(
              children: [
                const SizedBox(height: 60),
                _buildHeader(),
                const SizedBox(height: 40),
                Expanded(child: SingleChildScrollView(child: _buildForm())),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              colors: [Colors.amber.shade800, Colors.amber.shade400],
            ),
          ),
          child: const Icon(Icons.person_add, color: Colors.white, size: 40),
        ),
        const SizedBox(height: 16),
        const Text(
          '创建账号',
          style: TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildForm() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        LoginTextField(
          controller: _emailController,
          keyboardType: TextInputType.emailAddress,
          icon: Icons.email_outlined,
          hintText: '请输入邮箱',
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
              isLoading: _isLoading,
            ),
          ],
        ),
        const SizedBox(height: 16),
        LoginTextField(
          controller: _passwordController,
          keyboardType: TextInputType.visiblePassword,
          icon: Icons.lock,
          hintText: '请输入密码（至少6位）',
          obscureText: true,
        ),
        const SizedBox(height: 16),
        LoginTextField(
          controller: _confirmController,
          keyboardType: TextInputType.visiblePassword,
          icon: Icons.lock_outline,
          hintText: '请确认密码',
          obscureText: true,
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _register,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.amber.shade700,
              padding: const EdgeInsets.symmetric(vertical: 16),
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
                : const Text(
                    '注册',
                    style: TextStyle(
                      color: Colors.black,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
          ),
        ),
        const SizedBox(height: 16),
        TextButton(
          onPressed: () => context.go('/login'),
          child: const Text(
            '已有账号？去登录',
            style: TextStyle(color: Colors.white54, fontSize: 14),
          ),
        ),
      ],
    );
  }
}
