import 'package:flutter/material.dart';

/// 四维度标签组（支持中英文 key）
class FourDimsWidget extends StatelessWidget {
  final Map<String, dynamic> dims;

  const FourDimsWidget({super.key, required this.dims});

  static const _labels = {
    'competitiveness': '竞争力',
    '竞争': '竞争力',
    'growth': '成长性',
    '盈利': '成长性',
    'valuation': '估值',
    '客户': '估值',
    'certainty': '确定性',
    '技术': '确定性',
  };

  static Color _levelColor(String level) {
    switch (level) {
      case '高': return const Color(0xFFE53935);
      case '中': return const Color(0xFFFFB300);
      case '低': return const Color(0xFF43A047);
      default: return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final pairs = <MapEntry<String, String>>[];

    for (final entry in dims.entries) {
      final label = _labels[entry.key] ?? entry.key;
      pairs.add(MapEntry(label, entry.value.toString()));
    }

    return Wrap(
      spacing: 8,
      runSpacing: 6,
      children: [
        for (final pair in pairs)
          _DimChip(label: pair.key, level: pair.value),
      ],
    );
  }
}

class _DimChip extends StatelessWidget {
  final String label;
  final String level;

  const _DimChip({required this.label, required this.level});

  Color get _color {
    switch (level) {
      case '高': return const Color(0xFFE53935);
      case '中': return const Color(0xFFFFB300);
      case '低': return const Color(0xFF43A047);
      default: return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: _color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
          const SizedBox(width: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            decoration: BoxDecoration(
              color: _color,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              level,
              style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }
}