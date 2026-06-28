import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/news_item.dart';
import '../../data/repositories/news_repository.dart';

/// 新闻列表状态
class NewsListState {
  final List<NewsItem> hotNews;
  final List<NewsItem> latestNews;
  final List<NewsItem> historyNews;
  final String viewMode; // 'hot' | 'latest' | 'history'
  final String batchTime;
  final bool isLoading;
  final String? errorMessage;

  const NewsListState({
    this.hotNews = const [],
    this.latestNews = const [],
    this.historyNews = const [],
    this.viewMode = 'hot',
    this.batchTime = '',
    this.isLoading = false,
    this.errorMessage,
  });

  List<NewsItem> get currentNews {
    switch (viewMode) {
      case 'hot':
        return hotNews;
      case 'latest':
        return latestNews;
      case 'history':
        return historyNews;
      default:
        return hotNews;
    }
  }

  NewsListState copyWith({
    List<NewsItem>? hotNews,
    List<NewsItem>? latestNews,
    List<NewsItem>? historyNews,
    String? viewMode,
    String? batchTime,
    bool? isLoading,
    String? errorMessage,
  }) {
    return NewsListState(
      hotNews: hotNews ?? this.hotNews,
      latestNews: latestNews ?? this.latestNews,
      historyNews: historyNews ?? this.historyNews,
      viewMode: viewMode ?? this.viewMode,
      batchTime: batchTime ?? this.batchTime,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
    );
  }
}

/// News Notifier
class NewsListNotifier extends StateNotifier<NewsListState> {
  final NewsRepository _repository = NewsRepository();

  NewsListNotifier() : super(const NewsListState());

  /// 加载新闻
  Future<void> loadNews() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    await _loadAllNews();
    state = state.copyWith(isLoading: false);
  }

  Future<void> _loadAllNews() async {
    final all = await _repository.fetchAllNews();
    state = state.copyWith(
      hotNews: all['hot'] ?? [],
      latestNews: all['latest'] ?? [],
      historyNews: all['history'] ?? [],
    );
  }

  /// 切换视图模式
  void switchViewMode(String mode) {
    if (state.viewMode != mode) {
      state = state.copyWith(viewMode: mode);
    }
  }

  /// 下拉刷新 - 重新拉取全部，再按当前视图显示
  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    final all = await _repository.fetchAllNews();
    state = state.copyWith(
      hotNews: all['hot'] ?? [],
      latestNews: all['latest'] ?? [],
      historyNews: all['history'] ?? [],
      isLoading: false,
    );
  }
}

/// Provider
final newsListProvider = StateNotifierProvider<NewsListNotifier, NewsListState>((ref) {
  return NewsListNotifier();
});