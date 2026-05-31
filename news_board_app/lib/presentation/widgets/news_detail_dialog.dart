import 'package:flutter/material.dart';
import '../../data/models/news_item.dart';
import 'news_detail_sector_section.dart';
import 'news_detail_stocks_section.dart';
import 'comment_section.dart';
import 'feedback_dialog.dart';

/// 新闻详情弹窗
class NewsDetailDialog extends StatelessWidget {
  final NewsItem news;

  const NewsDetailDialog({super.key, required this.news});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A1A),
      body: SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeader(context),
                if (news.summary.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _buildSummary(),
                ],
                if (news.reason.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _buildReason(),
                ],
                if (news.sectorList.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  NewsDetailSectorSection(
                    sectors: news.sectorList,
                    sectorChanges: news.sectorChanges,
                  ),
                ],
                if (news.coreStocksPreview.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  NewsDetailStocksSection(stocks: news.coreStocksPreview),
                ],
                const SizedBox(height: 20),
                CommentSection(newsId: news.id),
                const SizedBox(height: 16),
                _buildFeedbackButton(context),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            news.title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.bold,
              height: 1.4,
            ),
          ),
        ),
        IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.close, color: Colors.white54),
        ),
      ],
    );
  }

  Widget _buildSummary() {
    return _buildInfoBox(
      label: '摘要',
      labelColor: Colors.amber,
      content: news.summary,
      bgColor: Colors.white.withOpacity(0.05),
      borderColor: Colors.transparent,
    );
  }

  Widget _buildReason() {
    return _buildInfoBox(
      label: '推荐逻辑',
      labelColor: Colors.amber,
      content: news.reason,
      bgColor: Colors.amber.withOpacity(0.1),
      borderColor: Colors.amber.withOpacity(0.3),
      icon: Icons.lightbulb_outline,
    );
  }

  Widget _buildInfoBox({
    required String label,
    required Color labelColor,
    required String content,
    required Color bgColor,
    required Color borderColor,
    IconData? icon,
  }) {
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
          Row(
            children: [
              if (icon != null) ...[
                Icon(icon, color: labelColor, size: 16),
                const SizedBox(width: 6),
              ],
              Text(label, style: TextStyle(color: labelColor, fontSize: 13, fontWeight: FontWeight.w600)),
            ],
          ),
          const SizedBox(height: 8),
          Text(content, style: const TextStyle(color: Colors.white70, fontSize: 14, height: 1.5)),
        ],
      ),
    );
  }

  Widget _buildFeedbackButton(BuildContext context) {
    return Center(
      child: TextButton.icon(
        onPressed: () => showDialog(context: context, builder: (_) => const FeedbackDialog()),
        icon: const Icon(Icons.feedback_outlined, color: Colors.white38, size: 18),
        label: const Text('意见建议', style: TextStyle(color: Colors.white38, fontSize: 13)),
      ),
    );
  }
}