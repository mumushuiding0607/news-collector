import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/providers/news_provider.dart';
import '../../core/providers/auth_provider.dart';
import '../widgets/news_card.dart';
import '../widgets/side_drawer.dart';

class NewsListPage extends ConsumerStatefulWidget {
  const NewsListPage({super.key});

  @override
  ConsumerState<NewsListPage> createState() => _NewsListPageState();
}

class _NewsListPageState extends ConsumerState<NewsListPage> with SingleTickerProviderStateMixin {
  late final AnimationController _headerController;
  late final CurvedAnimation _headerAnimation;

  @override
  void initState() {
    super.initState();
    _headerController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _headerAnimation = CurvedAnimation(
      parent: _headerController,
      curve: Curves.easeOut,
    );
    _headerController.forward();
    Future.microtask(() => ref.read(newsListProvider.notifier).loadNews());
  }

  @override
  void dispose() {
    _headerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(gradient: _buildBgGradient()),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(),
              Expanded(child: _buildContent()),
            ],
          ),
        ),
      ),
    );
  }

  LinearGradient _buildBgGradient() {
    return const LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: [Color(0xFF0A0A0A), Color(0xFF121212), Color(0xFF0A0A0A)],
      stops: [0.0, 0.5, 1.0],
    );
  }

  Widget _buildHeader() {
    final authState = ref.watch(authProvider);

    return AnimatedBuilder(
      animation: _headerAnimation,
      builder: (context, child) {
        return Opacity(
          opacity: _headerAnimation.value,
          child: Transform.translate(
            offset: Offset(0, -20 * (1 - _headerAnimation.value)),
            child: child,
          ),
        );
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Row(
          children: [
            if (authState.isLoggedIn)
              IconButton(
                icon: const Icon(Icons.menu, color: Colors.white70),
                onPressed: () => _showSideDrawer(context),
              ),
            _buildTitle(),
            const Spacer(),
            _buildModeToggle(),
          ],
        ),
      ),
    );
  }

  Widget _buildTitle() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ShaderMask(
          shaderCallback: (bounds) => const LinearGradient(
            colors: [Colors.white, Color(0xFFE8E8E8)],
          ).createShader(bounds),
          child: const Text(
            '市场风向标',
            style: TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w800,
              letterSpacing: 1,
              height: 1.2,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            _buildLiveDot(),
            const SizedBox(width: 8),
            const Text(
              '实时跟踪',
              style: TextStyle(
                color: Colors.white54,
                fontSize: 12,
                letterSpacing: 2,
                fontWeight: FontWeight.w300,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildLiveDot() {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppTheme.accentGreen,
        boxShadow: [
          BoxShadow(color: AppTheme.accentGreen.withOpacity(0.5), blurRadius: 8),
        ],
      ),
    );
  }

  Widget _buildModeToggle() {
    final newsState = ref.watch(newsListProvider);

    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildToggleBtn('热点', 'hot', newsState.viewMode),
          _buildToggleBtn('最新', 'latest', newsState.viewMode),
          _buildToggleBtn('历史', 'history', newsState.viewMode),
        ],
      ),
    );
  }

  Widget _buildToggleBtn(String label, String mode, String currentMode) {
    final selected = currentMode == mode;
    return GestureDetector(
      onTap: () => ref.read(newsListProvider.notifier).switchViewMode(mode),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? Colors.white.withOpacity(0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : Colors.white54,
            fontSize: 13,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }

  Widget _buildContent() {
    final newsState = ref.watch(newsListProvider);

    if (newsState.isLoading && newsState.currentNews.isEmpty) return _buildLoading();
    if (newsState.errorMessage != null && newsState.currentNews.isEmpty) return _buildError(newsState.errorMessage!);
    if (newsState.currentNews.isEmpty) return _buildEmpty();

    return RefreshIndicator(
      onRefresh: () => ref.read(newsListProvider.notifier).refresh(),
      color: AppTheme.accentGold,
      backgroundColor: const Color(0xFF1A1A1A),
      child: _buildList(newsState),
    );
  }

  Widget _buildLoading() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(width: 60, height: 60, child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.accentGold)),
          SizedBox(height: 20),
          Text('加载中...', style: TextStyle(color: Colors.white54, fontSize: 14)),
        ],
      ),
    );
  }

  Widget _buildError(String msg) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, color: Colors.red, size: 48),
          const SizedBox(height: 16),
          Text(msg, style: const TextStyle(color: Colors.white54)),
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => ref.read(newsListProvider.notifier).loadNews(),
            child: const Text('重试', style: TextStyle(color: Colors.amber)),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    final newsState = ref.watch(newsListProvider);
    String msg = '暂无数据';
    if (newsState.viewMode == 'hot') msg = '暂无热点新闻';
    if (newsState.viewMode == 'latest') msg = '暂无最新新闻';

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.inbox_outlined, color: Colors.white24, size: 64),
          const SizedBox(height: 16),
          Text(msg, style: const TextStyle(color: Colors.white38, fontSize: 16)),
        ],
      ),
    );
  }

  Widget _buildList(NewsListState newsState) {
    final news = newsState.currentNews;
    final viewMode = newsState.viewMode;

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      itemCount: news.length,
      itemBuilder: (_, i) {
        final isLocked = _shouldLock(i, viewMode, news);
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: NewsCard(news: news[i], isLocked: isLocked),
        );
      },
    );
  }

  bool _shouldLock(int index, String viewMode, List news) {
    if (viewMode != 'hot' && viewMode != 'latest') return false;
    if (index >= 1) return false;
    if (index >= news.length) return false;
    final authState = ref.read(authProvider);
    if (authState.subscriptionLevel != 'free') return false;
    return true;
  }

  void _showSideDrawer(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1A1A1A),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.8,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        expand: false,
        builder: (_, scrollController) => SideDrawer(scrollController: scrollController),
      ),
    );
  }
}