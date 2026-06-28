import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/utils/widget_capture.dart';
import '../../data/models/news_item.dart';
import 'news_detail_sector_section.dart';
import 'news_detail_stocks_section.dart';
import 'news_card_evaluation.dart';
import 'comment_section.dart';
import 'feedback_dialog.dart';
import 'share_sheet.dart';

/// 新闻详情弹窗
class NewsDetailDialog extends ConsumerStatefulWidget {
  final NewsItem news;

  const NewsDetailDialog({super.key, required this.news});

  @override
  ConsumerState<NewsDetailDialog> createState() => _NewsDetailDialogState();
}

class _NewsDetailDialogState extends ConsumerState<NewsDetailDialog> {
  bool _isCapturing = false;

  Future<void> _onShare() async {
    if (_isCapturing) return;

    // Web 平台暂不支持截图
    if (kIsWeb) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Web 平台暂不支持分享图片，请使用移动端')),
      );
      return;
    }

    setState(() { _isCapturing = true; });

    try {
      // 直接对当前页面内容截图（视觉与页面完全一致）
      // includeInteractive: false 跳过评论区/反馈按钮，避免 MouseTracker 断言
      final bytes = await WidgetCapture.capture(
        context: context,
        pixelRatio: 2.5,
        builder: (ctx) => _buildBody(includeInteractive: false),
      );

      if (!mounted) return;

      if (bytes == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('图片生成失败')),
        );
        return;
      }

      // 弹出分享弹窗显示图片
      ShareSheet.showWithImage(context, widget.news, bytes);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('分享失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() { _isCapturing = false; });
      }
    }
  }

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
                const SizedBox(height: 16),
                _buildBody(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// 构建新闻详情主体内容（被 build 和 _onShare 共用）
  ///
  /// [includeInteractive] 是否包含交互组件（评论、反馈按钮）。
  /// 截图时传 false，避免在 Overlay 中渲染交互组件触发 MouseTracker 断言。
  Widget _buildBody({bool includeInteractive = true}) {
    final news = widget.news;
    final hasEvaluation = news.direction != null ||
        news.intensity != null ||
        news.expectedChange != null ||
        news.duration != null ||
        news.expectationLevel != null ||
        news.marketMode != null ||
        news.maxSectorRise != null;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (news.summary.isNotEmpty) ...[
          _buildInfoBox(
            label: '摘要',
            labelColor: Colors.amber,
            content: news.summary,
            bgColor: Colors.white.withValues(alpha: 0.05),
            borderColor: Colors.transparent,
          ),
          const SizedBox(height: 16),
        ],
        if (news.reason.isNotEmpty) ...[
          _buildInfoBox(
            label: '推荐逻辑',
            labelColor: Colors.amber,
            content: news.reason,
            bgColor: Colors.amber.withValues(alpha: 0.1),
            borderColor: Colors.amber.withValues(alpha: 0.3),
            icon: Icons.lightbulb_outline,
          ),
          const SizedBox(height: 16),
        ],
        if (hasEvaluation) ...[
          _buildInfoBox(
            label: '评价属性',
            labelColor: Colors.blueAccent,
            contentWidget: NewsCardEvaluation(news: news, showAll: true),
            bgColor: Colors.blueAccent.withValues(alpha: 0.08),
            borderColor: Colors.blueAccent.withValues(alpha: 0.25),
            icon: Icons.analytics_outlined,
          ),
          const SizedBox(height: 16),
        ],
        if (news.sectorList.isNotEmpty) ...[
          NewsDetailSectorSection(
            sectors: news.sectorList,
            currentChangeRates: news.currentChangeRateList,
            sectorChanges: news.sectorChanges,
          ),
          const SizedBox(height: 16),
        ],
        if (news.coreStocksPreview.isNotEmpty) ...[
          NewsDetailStocksSection(stocks: news.coreStocksPreview),
          const SizedBox(height: 16),
        ],
        if (includeInteractive) ...[
          const SizedBox(height: 4),
          CommentSection(newsId: news.id),
          const SizedBox(height: 16),
          Center(
            child: TextButton.icon(
              onPressed: () => _showFeedback(context),
              icon: const Icon(Icons.feedback_outlined, color: Colors.white38, size: 18),
              label: const Text('意见建议', style: TextStyle(color: Colors.white38, fontSize: 13)),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            widget.news.title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.bold,
              height: 1.4,
            ),
          ),
        ),
        IconButton(
          onPressed: _isCapturing ? null : _onShare,
          icon: _isCapturing
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white54),
                )
              : const Icon(Icons.share, color: Colors.white54),
        ),
        IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.close, color: Colors.white54),
        ),
      ],
    );
  }

  Widget _buildInfoBox({
    required String label,
    required Color labelColor,
    String? content,
    Widget? contentWidget,
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
          if (contentWidget != null)
            contentWidget
          else
            Text(content ?? '', style: const TextStyle(color: Colors.white70, fontSize: 14, height: 1.5)),
        ],
      ),
    );
  }

  void _showFeedback(BuildContext ctx) {
    showGeneralDialog(
      context: ctx,
      barrierDismissible: true,
      barrierLabel: '关闭',
      barrierColor: Colors.black87,
      transitionDuration: const Duration(milliseconds: 300),
      pageBuilder: (context, animation, secondaryAnimation) => const FeedbackDialog(),
    );
  }
}
