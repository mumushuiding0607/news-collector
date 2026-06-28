import 'package:flutter/material.dart';
import '../../data/models/news_item.dart';
import 'four_dims_widget.dart';

/// 核心标的展开状态管理
final _expandedStocks = <int, bool>{};

/// 详情页-核心标的区块（可折叠）
class NewsDetailStocksSection extends StatefulWidget {
  final List<CoreStockPreview> stocks;

  const NewsDetailStocksSection({super.key, required this.stocks});

  @override
  State<NewsDetailStocksSection> createState() => _NewsDetailStocksSectionState();
}

class _NewsDetailStocksSectionState extends State<NewsDetailStocksSection> {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.amber.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.amber.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(),
          const SizedBox(height: 12),
          ...widget.stocks.asMap().entries.map((e) => _buildStockEntry(e.key, e.value)),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        const Icon(Icons.star, color: Colors.amber, size: 16),
        const SizedBox(width: 6),
        Text(
          '核心标的详情 (${widget.stocks.length})',
          style: const TextStyle(color: Colors.amber, fontSize: 13, fontWeight: FontWeight.w600),
        ),
        const Spacer(),
        GestureDetector(
          onTap: _toggleAll,
          child: Text(
            _allExpanded ? '全部收起' : '全部展开',
            style: const TextStyle(color: Colors.white38, fontSize: 12),
          ),
        ),
      ],
    );
  }

  bool get _allExpanded => widget.stocks.every((s) => _expandedStocks[s.hashCode] == true);

  void _toggleAll() {
    setState(() {
      for (final s in widget.stocks) {
        _expandedStocks[s.hashCode] = _allExpanded ? false : true;
      }
    });
  }

  Widget _buildStockEntry(int index, CoreStockPreview stock) {
    final isExpanded = _expandedStocks[stock.hashCode] ?? false;
    final hasFullData = stock.hasFullData;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: Column(
          children: [
            _buildStockHeader(stock, isExpanded, hasFullData),
            if (isExpanded) _buildExpandedContent(stock),
          ],
        ),
      ),
    );
  }

  Widget _buildStockHeader(CoreStockPreview stock, bool isExpanded, bool hasFullData) {
    return InkWell(
      onTap: () => setState(() => _expandedStocks[stock.hashCode] = !isExpanded),
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.amber.withOpacity(hasFullData ? 0.3 : 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(stock.tier, style: TextStyle(color: Colors.amber.shade300, fontSize: 11)),
            ),
            const SizedBox(width: 8),
            Expanded(child: Text(stock.name, style: const TextStyle(color: Colors.white, fontSize: 14))),
            Text(stock.sector, style: const TextStyle(color: Colors.white38, fontSize: 12)),
            const SizedBox(width: 8),
            Icon(isExpanded ? Icons.expand_less : Icons.expand_more, color: Colors.white38, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildExpandedContent(CoreStockPreview stock) {
    if (!stock.hasFullData) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(color: Colors.white12, height: 1),
          const SizedBox(height: 10),
          if (stock.chainLink != null && stock.chainLink!.isNotEmpty)
            _buildFieldRow('护城河', stock.chainLink!),
          if (stock.fourDims != null && stock.fourDims!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(width: 60, child: Text('四维度:', style: TextStyle(color: Colors.white54, fontSize: 12))),
                Expanded(child: FourDimsWidget(dims: stock.fourDims!)),
              ],
            ),
          ],
          if (stock.moat != null && stock.moat!.isNotEmpty) ...[
            const SizedBox(height: 8),
            _buildFieldRow('核心逻辑', stock.moat!),
          ],
          if (stock.hasPriceChange) ...[
            const SizedBox(height: 10),
            _buildPriceChanges(stock),
          ],
        ],
      ),
    );
  }

  Widget _buildPriceChanges(CoreStockPreview stock) {
    final items = <Widget>[];

    if (stock.d1 != null && stock.d1!.isNotEmpty) {
      items.add(_buildPriceChangeChip('当天', stock.d1!));
    }
    if (stock.d2 != null && stock.d2!.isNotEmpty) {
      items.add(_buildPriceChangeChip('+1天', stock.d2!));
    }
    if (stock.d3 != null && stock.d3!.isNotEmpty) {
      items.add(_buildPriceChangeChip('+2天', stock.d3!));
    }

    if (items.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('涨跌追踪', style: TextStyle(color: Colors.white54, fontSize: 11, fontWeight: FontWeight.w500)),
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: items,
        ),
      ],
    );
  }

  Widget _buildPriceChangeChip(String label, String value) {
    // 解析数值，正数为红色，负数为绿色
    final numValue = double.tryParse(value.replaceAll('%', ''));
    final isPositive = numValue != null && numValue > 0;
    final isNegative = numValue != null && numValue < 0;
    final displayValue = value.endsWith('%') ? value : '$value%';

    Color textColor = Colors.white70;
    if (isPositive) {
      textColor = const Color(0xFFEF4444); // 红色
    } else if (isNegative) {
      textColor = const Color(0xFF22C55E); // 绿色
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: textColor.withOpacity(0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: textColor.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 10)),
          const SizedBox(width: 4),
          Text(
            displayValue,
            style: TextStyle(color: textColor, fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildFieldRow(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(width: 60, child: Text('$label:', style: const TextStyle(color: Colors.white54, fontSize: 12))),
        Expanded(child: Text(value, style: const TextStyle(color: Colors.white70, fontSize: 12))),
      ],
    );
  }
}