import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class AnimatedChangeText extends StatefulWidget {
  final double change;
  final TextStyle? style;
  final bool showSign;

  const AnimatedChangeText({
    super.key,
    required this.change,
    this.style,
    this.showSign = true,
  });

  @override
  State<AnimatedChangeText> createState() => _AnimatedChangeTextState();
}

class _AnimatedChangeTextState extends State<AnimatedChangeText>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _animation = Tween<double>(begin: 0, end: widget.change).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
    _controller.forward();
  }

  @override
  void didUpdateWidget(AnimatedChangeText oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.change != widget.change) {
      _animation = Tween<double>(begin: _animation.value, end: widget.change).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
      );
      _controller.reset();
      _controller.forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String _formatValue(double value) {
    final sign = widget.showSign && value > 0 ? '+' : '';
    return '$sign${value.toStringAsFixed(2)}';
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        final color = AppTheme.getChangeColor(_animation.value);
        return Text(
          _formatValue(_animation.value),
          style: (widget.style ?? const TextStyle()).copyWith(
            color: color,
            fontWeight: FontWeight.bold,
          ),
        );
      },
    );
  }
}

class ChangeIndicator extends StatelessWidget {
  final double change;
  final double iconSize;

  const ChangeIndicator({
    super.key,
    required this.change,
    this.iconSize = 16,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppTheme.getChangeColor(change);
    final isPositive = change > 0;
    final isNeutral = change == 0;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          isNeutral
              ? Icons.remove
              : isPositive
                  ? Icons.arrow_upward
                  : Icons.arrow_downward,
          color: color,
          size: iconSize,
        ),
        const SizedBox(width: 4),
        AnimatedChangeText(change: change),
      ],
    );
  }
}