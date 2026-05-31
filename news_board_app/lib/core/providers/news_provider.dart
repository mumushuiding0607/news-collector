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
    try {
      await _loadAllNews();
      state = state.copyWith(isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<void> _loadAllNews() async {
    final results = await Future.wait([
      _repository.fetchHotNews(),
      _repository.fetchLatestNews(),
      _repository.fetchHistoryNews(),
    ]);
    state = state.copyWith(
      hotNews: results[0],
      latestNews: results[1],
      historyNews: results[2],
    );
  }

  /// 切换视图模式
  void switchViewMode(String mode) {
    if (state.viewMode != mode) {
      state = state.copyWith(viewMode: mode);
    }
  }

  /// 下拉刷新 - 只刷新当前视图
  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      switch (state.viewMode) {
        case 'hot':
          state = state.copyWith(hotNews: await _repository.fetchHotNews(), isLoading: false);
          break;
        case 'latest':
          state = state.copyWith(latestNews: await _repository.fetchLatestNews(), isLoading: false);
          break;
        case 'history':
          state = state.copyWith(historyNews: await _repository.fetchHistoryNews(), isLoading: false);
          break;
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }
}

/// Provider
final newsListProvider = StateNotifierProvider<NewsListNotifier, NewsListState>((ref) {
  return NewsListNotifier();
});