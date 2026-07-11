import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 隐私政策同意弹窗（首次启动时强制显示）
class PrivacyConsentDialog extends StatefulWidget {
  final VoidCallback onAgree;
  final VoidCallback onDisagree;

  const PrivacyConsentDialog({
    super.key,
    required this.onAgree,
    required this.onDisagree,
  });

  @override
  State<PrivacyConsentDialog> createState() => _PrivacyConsentDialogState();
}

class _PrivacyConsentDialogState extends State<PrivacyConsentDialog> {
  final ScrollController _scrollController = ScrollController();
  bool _hasScrolledToBottom = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 20) {
      if (!_hasScrolledToBottom) {
        setState(() => _hasScrolledToBottom = true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF1E1E1E),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                '隐私政策',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              const Text(
                '请您在使用本应用前仔细阅读并了解我们的隐私政策',
                style: TextStyle(color: Colors.white54, fontSize: 13),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Container(
                height: 250,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: SingleChildScrollView(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    _privacyPolicyText,
                    style: const TextStyle(color: Colors.white70, fontSize: 14, height: 1.6),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              if (!_hasScrolledToBottom)
                const Text(
                  '请向下滚动阅读全部内容',
                  style: TextStyle(color: Colors.amber, fontSize: 12),
                  textAlign: TextAlign.center,
                ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: widget.onDisagree,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white54,
                        side: const BorderSide(color: Colors.white24),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      child: const Text('不同意'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: widget.onAgree,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.amber.shade700,
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      child: const Text('同意', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 检查是否已同意隐私政策
Future<bool> checkPrivacyConsent() async {
  final prefs = await SharedPreferences.getInstance();
  return prefs.getBool('privacy_consent') ?? false;
}

/// 隐私政策闸门：未同意时先显示弹窗，同意后切换到正式 App
class PrivacyGate extends StatefulWidget {
  final Widget child;

  const PrivacyGate({super.key, required this.child});

  @override
  State<PrivacyGate> createState() => _PrivacyGateState();
}

class _PrivacyGateState extends State<PrivacyGate> {
  bool _showDialog = true;

  Future<void> _agree() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('privacy_consent', true);
    if (mounted) setState(() => _showDialog = false);
  }

  Future<void> _disagree() async {
    SystemNavigator.pop();
  }

  @override
  Widget build(BuildContext context) {
    if (!_showDialog) return widget.child;

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      home: Scaffold(
        body: PrivacyConsentDialog(
          onAgree: _agree,
          onDisagree: _disagree,
        ),
      ),
    );
  }
}

const String _privacyPolicyText = '''
隐私政策

感谢您使用本应用。我们高度重视您的个人信息保护，本政策旨在向您说明我们收集、使用、存储和保护您信息的方式。

一、信息收集
1. 设备信息：包括设备型号、操作系统版本、屏幕分辨率等，用于优化应用体验。
2. 网络信息：IP 地址、网络类型，用于保障服务安全。
3. 您主动提供的信息：注册时填写的邮箱账号等。

二、信息用途
1. 提供、维护和改进我们的服务。
2. 保障账号安全，防止异常登录。
3. 向您推送您可能感兴趣的资讯内容。

三、信息共享
我们不会将您的个人信息出售给第三方。在以下情况下，我们可能披露您的信息：
- 法律要求时
- 保护我们的合法权益时

四、信息安全
我们采用行业标准的安全措施保护您的数据，防止数据遭到未经授权的访问、使用或泄露。

五、用户权利
您有权：
- 查阅我们持有的您的个人信息
- 更正不准确的信息
- 删除您的账号及相关信息
- 撤回同意（但不影响撤回前已进行的处理）

六、联系我们
如您对本隐私政策有任何疑问，请通过应用内反馈功能联系我们。

七、变更通知
我们可能会不时更新本政策，届时将通过应用内公告方式通知您。继续使用本应用即表示您接受更新后的政策。
''';
