import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
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
    final config = ref.watch(configProvider);
    final theme = ref.watch(effectiveThemeProvider);

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(gradient: theme.backgroundGradient),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(config, theme),
              Expanded(child: _buildContent(config, theme)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(AppConfig config, ThemeConfig theme) {
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
        padding: const EdgeInsets.only(left: 8, right: 20, top: 16, bottom: 16),
        child: Row(
          children: [
            IconButton(
              icon: Icon(Icons.menu, color: theme.textPrimaryColor.withOpacity(0.7)),
              onPressed: () => _showSideDrawer(context),
            ),
            _buildTitle(config, theme),
            const Spacer(),
            _buildThemeToggle(theme),
            const SizedBox(width: 8),
            _buildModeToggle(theme, config),
          ],
        ),
      ),
    );
  }

  Widget _buildTitle(AppConfig config, ThemeConfig theme) {
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == AppThemeMode.dark;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 标题：暗色模式用渐变，亮色模式用纯色
        isDark
            ? ShaderMask(
                shaderCallback: (bounds) => LinearGradient(
                  colors: [theme.textPrimaryColor, theme.textPrimaryColor.withOpacity(0.9)],
                ).createShader(bounds),
                child: Text(
                  config.home.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                    height: 1.2,
                  ),
                ),
              )
            : Text(
                config.home.title,
                style: TextStyle(
                  color: theme.textPrimaryColor,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1,
                  height: 1.2,
                ),
              ),
        const SizedBox(height: 4),
        Row(
          children: [
            _buildLiveDot(theme),
            const SizedBox(width: 8),
            Text(
              config.home.subtitle,
              style: TextStyle(
                color: theme.textSecondaryColor,
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

  Widget _buildLiveDot(ThemeConfig theme) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: theme.accentGreenColor,
        boxShadow: [
          BoxShadow(color: theme.accentGreenColor.withOpacity(0.5), blurRadius: 8),
        ],
      ),
    );
  }

  Widget _buildThemeToggle(ThemeConfig theme) {
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == AppThemeMode.dark;

    return GestureDetector(
      onTap: () => ref.read(themeModeProvider.notifier).toggle(),
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: theme.textPrimaryColor.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: theme.textPrimaryColor.withOpacity(0.12)),
        ),
        child: Icon(
          isDark ? Icons.light_mode : Icons.dark_mode,
          color: theme.textPrimaryColor.withOpacity(0.7),
          size: 20,
        ),
      ),
    );
  }

  Widget _buildModeToggle(ThemeConfig theme, AppConfig config) {
    final newsState = ref.watch(newsListProvider);

    return Container(
      decoration: BoxDecoration(
        color: theme.textPrimaryColor.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: theme.textPrimaryColor.withOpacity(0.12)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildToggleBtn(config.uiTexts.newsList.tabHot, 'hot', newsState.viewMode, theme),
          _buildToggleBtn(config.uiTexts.newsList.tabLatest, 'latest', newsState.viewMode, theme),
          _buildToggleBtn(config.uiTexts.newsList.tabHistory, 'history', newsState.viewMode, theme),
        ],
      ),
    );
  }

  Widget _buildToggleBtn(String label, String mode, String currentMode, ThemeConfig theme) {
    final selected = currentMode == mode;
    return GestureDetector(
      onTap: () => ref.read(newsListProvider.notifier).switchViewMode(mode),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? theme.textPrimaryColor.withOpacity(0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? theme.textPrimaryColor : theme.textSecondaryColor,
            fontSize: 13,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }

  Widget _buildContent(AppConfig config, ThemeConfig theme) {
    final newsState = ref.watch(newsListProvider);

    if (newsState.isLoading && newsState.currentNews.isEmpty) return _buildLoading(config, theme);
    if (newsState.errorMessage != null && newsState.currentNews.isEmpty) return _buildError(newsState.errorMessage!, config, theme);
    if (newsState.currentNews.isEmpty) return _buildEmpty(newsState, config, theme);

    return RefreshIndicator(
      onRefresh: () => ref.read(newsListProvider.notifier).refresh(),
      color: theme.accentGoldColor,
      backgroundColor: theme.backgroundStartColor,
      child: _buildList(newsState),
    );
  }

  Widget _buildLoading(AppConfig config, ThemeConfig theme) {
    final texts = config.texts;
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(width: 60, height: 60, child: CircularProgressIndicator(strokeWidth: 2, color: theme.accentGoldColor)),
          const SizedBox(height: 20),
          Text(texts.loading, style: TextStyle(color: theme.textSecondaryColor, fontSize: 14)),
        ],
      ),
    );
  }

  Widget _buildError(String msg, AppConfig config, ThemeConfig theme) {
    final texts = config.texts;
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, color: theme.accentRedColor, size: 48),
          const SizedBox(height: 16),
          Text(msg, style: TextStyle(color: theme.textSecondaryColor)),
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => ref.read(newsListProvider.notifier).loadNews(),
            child: Text(texts.retry, style: TextStyle(color: theme.accentGoldColor)),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty(NewsListState newsState, AppConfig config, ThemeConfig theme) {
    final texts = config.texts;
    String msg = texts.emptyData;
    if (newsState.viewMode == 'hot') msg = texts.emptyHot;
    if (newsState.viewMode == 'latest') msg = texts.emptyLatest;

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.inbox_outlined, color: theme.textMutedColor, size: 64),
          const SizedBox(height: 16),
          Text(msg, style: TextStyle(color: theme.textMutedColor, fontSize: 16)),
        ],
      ),
    );
  }

  Widget _buildList(NewsListState newsState) {
    final news = newsState.currentNews;
    final viewMode = newsState.viewMode;
    final config = ref.watch(configProvider);
    final lockConfig = config.lock;

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      itemCount: news.length,
      itemBuilder: (_, i) {
        final isLocked = _shouldLock(i, viewMode, news, lockConfig.freeNewsLimit);
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: NewsCard(
            news: news[i],
            isLocked: isLocked,
            lockTitle: lockConfig.lockTitle,
            lockButtonLoggedIn: lockConfig.lockButtonLoggedIn,
            lockButtonNotLoggedIn: lockConfig.lockButtonNotLoggedIn,
          ),
        );
      },
    );
  }

  bool _shouldLock(int index, String viewMode, List news, int freeNewsLimit) {
    if (viewMode != 'hot' && viewMode != 'latest' && viewMode != 'history') return false;
    if (index >= freeNewsLimit) return false;
    if (index >= news.length) return false;
    final hasAccess = ref.read(hasSubscriptionAccessProvider);
    if (hasAccess) return false;
    return true;
  }

  void _showSideDrawer(BuildContext context) {
    final themeMode = ref.read(themeModeProvider);
    final isDark = themeMode == AppThemeMode.dark;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: isDark ? const Color(0xFF1A1A1A) : const Color(0xFFF8F6F3),
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