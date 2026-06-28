import 'package:flutter/material.dart';
import '../../shared/widgets/score_badge.dart';

/// 卡片头部：标题 + 分数徽章
class NewsCardHeader extends StatelessWidget {
  final String title;
  final int score;

  const NewsCardHeader({
    super.key,
    required this.title,
    required this.score,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.bold,
              height: 1.3,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 12),
        ScoreBadge(score: score, size: 42),
      ],
    );
  }
}
