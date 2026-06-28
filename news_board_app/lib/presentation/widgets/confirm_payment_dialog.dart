import 'package:flutter/material.dart';

class ConfirmPaymentDialog extends StatefulWidget {
  final Function(String note) onConfirm;

  const ConfirmPaymentDialog({super.key, required this.onConfirm});

  @override
  State<ConfirmPaymentDialog> createState() => _ConfirmPaymentDialogState();
}

class _ConfirmPaymentDialogState extends State<ConfirmPaymentDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF1E1E1E),
      title: const Text('是否已付款？', style: TextStyle(color: Colors.white)),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _controller,
            style: const TextStyle(color: Colors.white),
            decoration: InputDecoration(
              labelText: '转账备注或微信账号',
              labelStyle: const TextStyle(color: Colors.white54),
              hintText: '请输入转账备注或微信账号',
              hintStyle: const TextStyle(color: Colors.white24),
              filled: true,
              fillColor: Colors.white.withOpacity(0.08),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('取消', style: TextStyle(color: Colors.white54)),
        ),
        ElevatedButton(
          onPressed: () {
            final note = _controller.text.trim();
            if (note.isEmpty) {
              showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  content: const Text('请填写转账备注'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('确定')),
                  ],
                ),
              );
              return;
            }
            Navigator.pop(context);
            widget.onConfirm(note);
          },
          style: ElevatedButton.styleFrom(backgroundColor: Colors.amber.shade700),
          child: const Text('发送', style: TextStyle(color: Colors.white)),
        ),
      ],
    );
  }
}