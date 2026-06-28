import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../../core/providers/subscription_provider.dart';

class PaymentContent extends StatelessWidget {
  final String payMethod;
  final SubscriptionState subState;
  final VoidCallback onConfirmPayment;

  const PaymentContent({
    super.key,
    required this.payMethod,
    required this.subState,
    required this.onConfirmPayment,
  });

  @override
  Widget build(BuildContext context) {
    switch (payMethod) {
      case 'personal':
        return _PersonalPaymentView(
          imageBytes: subState.personalQrImageBytes,
          paymentConfirmed: subState.paymentConfirmed,
          onConfirm: onConfirmPayment,
        );
      case 'wechat':
        return _WechatPaymentView(
          codeUrl: subState.currentOrderCodeUrl ?? '',
        );
      default:
        return const SizedBox();
    }
  }
}

class _PersonalPaymentView extends StatelessWidget {
  final Uint8List? imageBytes;
  final bool paymentConfirmed;
  final VoidCallback onConfirm;

  const _PersonalPaymentView({
    required this.imageBytes,
    required this.paymentConfirmed,
    required this.onConfirm,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.2),
                blurRadius: 8,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: imageBytes != null
              ? Image.memory(
                  imageBytes!,
                  width: 240,
                  height: 320,
                  fit: BoxFit.contain,
                )
              : const SizedBox(
                  width: 240,
                  height: 320,
                  child: Center(child: CircularProgressIndicator()),
                ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.amber.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.amber.withOpacity(0.3)),
          ),
          child: const Column(
            children: [
              Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.amber, size: 20),
                  SizedBox(width: 8),
                  Text('扫码转账', style: TextStyle(color: Colors.amber, fontWeight: FontWeight.bold)),
                ],
              ),
              SizedBox(height: 8),
              Text(
                '付款备注：注册时的邮箱或手机号',
                style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (paymentConfirmed)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.green.withOpacity(0.3)),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.check_circle, color: Colors.green),
                SizedBox(width: 8),
                Text('已通知管理员，请等待激活', style: TextStyle(color: Colors.green)),
              ],
            ),
          )
        else
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: onConfirm,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.amber.shade700,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.question_mark, color: Colors.white),
              label: const Text('是否已付款', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          ),
      ],
    );
  }
}

class _WechatPaymentView extends StatelessWidget {
  final String codeUrl;

  const _WechatPaymentView({required this.codeUrl});

  @override
  Widget build(BuildContext context) {
    final isH5 = codeUrl.startsWith('http') && !codeUrl.contains('weixin://');

    if (codeUrl.isNotEmpty && !isH5) {
      return _buildQRCode(codeUrl);
    } else if (isH5) {
      return _buildH5PaymentTip();
    }
    return const SizedBox();
  }

  Widget _buildQRCode(String url) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Container(
            width: 200,
            height: 200,
            decoration: BoxDecoration(
              color: Colors.grey[200],
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Center(
              child: Text('QR Code\n(需集成 qr_flutter)', textAlign: TextAlign.center, style: TextStyle(fontSize: 14)),
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            '打开微信 → 扫一扫',
            style: TextStyle(color: Colors.black87, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildH5PaymentTip() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.green.withOpacity(0.15),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.green.withOpacity(0.3)),
      ),
      child: const Column(
        children: [
          Icon(Icons.phone_android, color: Colors.green, size: 48),
          SizedBox(height: 12),
          Text(
            '即将跳转到微信支付',
            style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 8),
          Text(
            '请在微信内点击支付链接完成付款',
            style: TextStyle(color: Colors.white70, fontSize: 14),
          ),
        ],
      ),
    );
  }
}