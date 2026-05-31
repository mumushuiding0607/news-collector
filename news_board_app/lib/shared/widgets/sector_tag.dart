import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class SectorTag extends StatelessWidget {
  final String name;
  final bool isHighlighted;

  const SectorTag({
    super.key,
    required this.name,
    this.isHighlighted = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: isHighlighted
            ? AppTheme.accentGold.withOpacity(0.2)
            : Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isHighlighted
              ? AppTheme.accentGold.withOpacity(0.5)
              : Colors.white.withOpacity(0.2),
          width: 1,
        ),
      ),
      child: Text(
        name,
        style: TextStyle(
          color: isHighlighted ? AppTheme.accentGold : Colors.white.withOpacity(0.8),
          fontSize: 12,
          fontWeight: isHighlighted ? FontWeight.w600 : FontWeight.normal,
        ),
      ),
    );
  }
}

class SectorTagList extends StatelessWidget {
  final List<String> sectors;

  const SectorTagList({
    super.key,
    required this.sectors,
  });

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: sectors.map((sector) {
        return SectorTag(name: sector);
      }).toList(),
    );
  }
}