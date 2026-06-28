import 'package:flutter/material.dart';

class PaymentStatusBadge extends StatelessWidget {
  final String status;

  const PaymentStatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    String statusText;
    Color statusColor;
    switch (status) {
      case 'paid':
        statusText = '支付成功';
        statusColor = Colors.green;
        break;
      case 'personal_pending':
        statusText = '待转账确认';
        statusColor = Colors.amber;
        break;
      case 'qr_created':
      case 'h5_created':
        statusText = '等待支付...';
        statusColor = Colors.amber;
        break;
      case 'mock':
        statusText = 'Mock 模式';
        statusColor = Colors.orange;
        break;
      default:
        statusText = '订单处理中...';
        statusColor = Colors.white54;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status != 'paid' && status != 'personal_pending')
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.amber),
            )
          else
            Icon(
              status == 'paid' ? Icons.check_circle : Icons.access_time,
              color: statusColor,
              size: 16,
            ),
          const SizedBox(width: 8),
          Text(statusText, style: TextStyle(color: statusColor)),
        ],
      ),
    );
  }
}