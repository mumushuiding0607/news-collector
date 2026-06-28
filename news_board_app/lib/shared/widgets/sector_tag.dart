import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';

class SectorTag extends ConsumerWidget {
  final String name;
  final bool isHighlighted;

  const SectorTag({
    super.key,
    required this.name,
    this.isHighlighted = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = ref.watch(configProvider).theme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: isHighlighted
            ? theme.accentGoldColor.withOpacity(0.2)
            : Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isHighlighted
              ? theme.accentGoldColor.withOpacity(0.5)
              : Colors.white.withOpacity(0.2),
          width: 1,
        ),
      ),
      child: Text(
        name,
        style: TextStyle(
          color: isHighlighted ? theme.accentGoldColor : Colors.white.withOpacity(0.8),
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