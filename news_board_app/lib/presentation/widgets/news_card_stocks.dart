import 'package:flutter/material.dart';
import '../../data/models/news_item.dart';

/// 核心标的预览
class NewsCardStocks extends StatelessWidget {
  final List<CoreStockPreview> stocks;

  const NewsCardStocks({super.key, required this.stocks});

  @override
  Widget build(BuildContext context) {
    if (stocks.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.star, color: Colors.amber, size: 12),
              SizedBox(width: 4),
              Text('核心标的', style: TextStyle(color: Colors.white54, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: stocks.take(4).map(_buildTag).toList()),
        ],
      ),
    );
  }

  Widget _buildTag(CoreStockPreview stock) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(stock.name, style: const TextStyle(color: Colors.white70, fontSize: 11)),
    );
  }
}
