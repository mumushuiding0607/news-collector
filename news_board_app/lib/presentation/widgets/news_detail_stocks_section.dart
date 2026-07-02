import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
import '../../data/models/news_item.dart';
import 'four_dims_widget.dart';

/// 核心标的展开状态管理
final _expandedStocks = <int, bool>{};

/// 详情页-核心标的区块（可折叠）
class NewsDetailStocksSection extends ConsumerStatefulWidget {
  final List<CoreStockPreview> stocks;

  const NewsDetailStocksSection({super.key, required this.stocks});

  @override
  ConsumerState<NewsDetailStocksSection> createState() => _NewsDetailStocksSectionState();
}

class _NewsDetailStocksSectionState extends ConsumerState<NewsDetailStocksSection> {
  @override
  Widget build(BuildContext context) {
    final isDark = ref.watch(themeModeProvider) == AppThemeMode.dark;
    final bgColor = isDark ? Colors.amber.withOpacity(0.08) : const Color(0xFFFFF3E0);
    final borderColor = isDark ? Colors.amber.withOpacity(0.2) : const Color(0xFFFFE0B2);
    final labelColor = isDark ? Colors.amber : const Color(0xFFE53935);
    final textMuted = isDark ? Colors.white38 : const Color(0xFF9B9B9B);
    final textPrimary = isDark ? Colors.white : const Color(0xFF1C1C1E);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(labelColor, textMuted, textPrimary),
          const SizedBox(height: 12),
          ...widget.stocks.asMap().entries.map((e) => _buildStockEntry(e.key, e.value, isDark, textPrimary, textMuted)),
        ],
      ),
    );
  }

  Widget _buildHeader(Color labelColor, Color textMuted, Color textPrimary) {
    return Row(
      children: [
        Icon(Icons.star, color: labelColor, size: 16),
        const SizedBox(width: 6),
        Text(
          '核心标的详情 (${widget.stocks.length})',
          style: TextStyle(color: labelColor, fontSize: 13, fontWeight: FontWeight.w600),
        ),
        const Spacer(),
        GestureDetector(
          onTap: _toggleAll,
          child: Text(
            _allExpanded ? '全部收起' : '全部展开',
            style: TextStyle(color: textMuted, fontSize: 12),
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

  Widget _buildStockEntry(int index, CoreStockPreview stock, bool isDark, Color textPrimary, Color textMuted) {
    final isExpanded = _expandedStocks[stock.hashCode] ?? false;
    final hasFullData = stock.hasFullData;
    final bgColor = isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04);
    final borderColor = isDark ? Colors.white.withOpacity(0.08) : Colors.grey.withOpacity(0.1);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: borderColor),
        ),
        child: Column(
          children: [
            _buildStockHeader(stock, isExpanded, hasFullData, isDark, textPrimary, textMuted),
            if (isExpanded) _buildExpandedContent(stock, isDark),
          ],
        ),
      ),
    );
  }

  Widget _buildStockHeader(CoreStockPreview stock, bool isExpanded, bool hasFullData, bool isDark, Color textPrimary, Color textMuted) {
    final labelColor = isDark ? Colors.amber : const Color(0xFFE53935);
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
                color: labelColor.withOpacity(hasFullData ? 0.3 : 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(stock.tier, style: TextStyle(color: labelColor.withOpacity(0.9), fontSize: 11)),
            ),
            const SizedBox(width: 8),
            Expanded(child: Text(stock.name, style: TextStyle(color: textPrimary, fontSize: 14))),
            Text(stock.sector, style: TextStyle(color: textMuted, fontSize: 12)),
            const SizedBox(width: 8),
            Icon(isExpanded ? Icons.expand_less : Icons.expand_more, color: textMuted, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildExpandedContent(CoreStockPreview stock, bool isDark) {
    if (!stock.hasFullData) return const SizedBox.shrink();
    final textMuted = isDark ? Colors.white54 : const Color(0xFF9B9B9B);
    final textColor = isDark ? Colors.white70 : const Color(0xFF5C5C5C);
    final dividerColor = isDark ? Colors.white12 : Colors.black.withOpacity(0.1);

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Divider(color: dividerColor, height: 1),
          const SizedBox(height: 10),
          if (stock.chainLink != null && stock.chainLink!.isNotEmpty)
            _buildFieldRow('护城河', stock.chainLink!, textMuted, textColor),
          if (stock.fourDims != null && stock.fourDims!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(width: 60, child: Text('四维度:', style: TextStyle(color: textMuted, fontSize: 12))),
                Expanded(child: FourDimsWidget(dims: stock.fourDims!)),
              ],
            ),
          ],
          if (stock.moat != null && stock.moat!.isNotEmpty) ...[
            const SizedBox(height: 8),
            _buildFieldRow('核心逻辑', stock.moat!, textMuted, textColor),
          ],
          if (stock.hasPriceChange) ...[
            const SizedBox(height: 10),
            _buildPriceChanges(stock, isDark),
          ],
        ],
      ),
    );
  }

  Widget _buildPriceChanges(CoreStockPreview stock, bool isDark) {
    final items = <Widget>[];

    if (stock.d1 != null && stock.d1!.isNotEmpty) {
      items.add(_buildPriceChangeChip('当天', stock.d1!, isDark));
    }
    if (stock.d2 != null && stock.d2!.isNotEmpty) {
      items.add(_buildPriceChangeChip('+1天', stock.d2!, isDark));
    }
    if (stock.d3 != null && stock.d3!.isNotEmpty) {
      items.add(_buildPriceChangeChip('+2天', stock.d3!, isDark));
    }

    if (items.isEmpty) return const SizedBox.shrink();

    final textMuted = isDark ? Colors.white54 : const Color(0xFF9B9B9B);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('涨跌追踪', style: TextStyle(color: textMuted, fontSize: 11, fontWeight: FontWeight.w500)),
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: items,
        ),
      ],
    );
  }

  Widget _buildPriceChangeChip(String label, String value, bool isDark) {
    final numValue = double.tryParse(value.replaceAll('%', ''));
    final isPositive = numValue != null && numValue > 0;
    final isNegative = numValue != null && numValue < 0;
    final displayValue = value.endsWith('%') ? value : '$value%';

    Color textColor = isDark ? Colors.white70 : const Color(0xFF5C5C5C);
    if (isPositive) {
      textColor = const Color(0xFFEF4444);
    } else if (isNegative) {
      textColor = const Color(0xFF22C55E);
    }

    final labelColor = isDark ? Colors.white.withOpacity(0.5) : Colors.black.withOpacity(0.4);

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
          Text(label, style: TextStyle(color: labelColor, fontSize: 10)),
          const SizedBox(width: 4),
          Text(
            displayValue,
            style: TextStyle(color: textColor, fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildFieldRow(String label, String value, Color textMuted, Color textColor) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(width: 60, child: Text('$label:', style: TextStyle(color: textMuted, fontSize: 12))),
        Expanded(child: Text(value, style: TextStyle(color: textColor, fontSize: 12))),
      ],
    );
  }
}