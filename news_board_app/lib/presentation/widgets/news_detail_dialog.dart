import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
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
        builder: (ctx) {
        final isDark = ref.watch(themeModeProvider) == AppThemeMode.dark;
        final captureMaxH = MediaQuery.of(context).size.height * 0.9;
        return _buildBody(includeInteractive: false, isDark: isDark, captureMaxHeight: captureMaxH);
      },
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
    final isDark = ref.watch(themeModeProvider) == AppThemeMode.dark;
    final bgColor = isDark ? const Color(0xFF1A1A1A) : const Color(0xFFF8F6F3);

    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(context, isDark),
              const SizedBox(height: 16),
              _buildBody(isDark: isDark),
            ],
          ),
        ),
      ),
    );
  }

  /// 构建新闻详情主体内容（被 build 和 _onShare 共用）
  ///
  /// [includeInteractive] 是否包含交互组件（评论、反馈按钮）。
  /// [captureMaxHeight] 截图时的最大高度，超出部分不截取（仅截图用，不影响正常显示）。
  Widget _buildBody({bool includeInteractive = true, required bool isDark, double? captureMaxHeight}) {
    final news = widget.news;
    final textMuted = isDark ? Colors.white54 : const Color(0xFF9B9B9B);
    final hasEvaluation = news.direction != null ||
        news.intensity != null ||
        news.expectedChange != null ||
        news.duration != null ||
        news.expectationLevel != null ||
        news.marketMode != null ||
        news.maxSectorRise != null;

    final body = Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (news.summary.isNotEmpty) ...[
          _buildInfoBox(
            label: '摘要',
            labelColor: isDark ? Colors.amber : const Color(0xFFE53935),
            content: news.summary,
            bgColor: isDark ? Colors.white.withValues(alpha: 0.05) : const Color(0xFFFFEBEE),
            borderColor: Colors.transparent,
            isDark: isDark,
          ),
          const SizedBox(height: 16),
        ],
        if (news.reason.isNotEmpty) ...[
          _buildInfoBox(
            label: '推荐逻辑',
            labelColor: isDark ? Colors.amber : const Color(0xFFE53935),
            content: news.reason,
            bgColor: isDark ? Colors.amber.withValues(alpha: 0.1) : const Color(0xFFFFF3E0),
            borderColor: isDark ? Colors.amber.withValues(alpha: 0.3) : const Color(0xFFFFE0B2),
            icon: Icons.lightbulb_outline,
            isDark: isDark,
          ),
          const SizedBox(height: 16),
        ],
        if (hasEvaluation) ...[
          _buildInfoBox(
            label: '评价属性',
            labelColor: isDark ? Colors.blueAccent : const Color(0xFF1976D2),
            contentWidget: NewsCardEvaluation(news: news, showAll: true),
            bgColor: isDark ? Colors.blueAccent.withValues(alpha: 0.08) : const Color(0xFFE3F2FD),
            borderColor: isDark ? Colors.blueAccent.withValues(alpha: 0.25) : const Color(0xFFBBDEFB),
            icon: Icons.analytics_outlined,
            isDark: isDark,
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
              icon: Icon(Icons.feedback_outlined, color: textMuted, size: 18),
              label: Text('意见建议', style: TextStyle(color: textMuted, fontSize: 13)),
            ),
          ),
        ],
      ],
    );

    // 截图时用 ConstrainedBox 限制高度，避免无限高导致变形
    if (captureMaxHeight != null) {
      return ConstrainedBox(
        constraints: BoxConstraints(maxHeight: captureMaxHeight),
        child: SingleChildScrollView(
          physics: const NeverScrollableScrollPhysics(),
          padding: const EdgeInsets.all(24),
          child: body,
        ),
      );
    }
    return body;
  }

  Widget _buildHeader(BuildContext context, bool isDark) {
    final textPrimary = isDark ? Colors.white : const Color(0xFF1C1C1E);
    final textMuted = isDark ? Colors.white54 : const Color(0xFF9B9B9B);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            widget.news.title,
            style: TextStyle(
              color: textPrimary,
              fontSize: 18,
              fontWeight: FontWeight.bold,
              height: 1.4,
            ),
          ),
        ),
        IconButton(
          onPressed: _isCapturing ? null : _onShare,
          icon: _isCapturing
              ? SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, color: textMuted),
                )
              : Icon(Icons.share, color: textMuted),
        ),
        IconButton(
          onPressed: () => Navigator.pop(context),
          icon: Icon(Icons.close, color: textMuted),
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
    required bool isDark,
  }) {
    final textColor = isDark ? Colors.white70 : const Color(0xFF5C5C5C);
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
            Text(content ?? '', style: TextStyle(color: textColor, fontSize: 14, height: 1.5)),
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
