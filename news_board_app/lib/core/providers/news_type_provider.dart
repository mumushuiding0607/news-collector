import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../main.dart';

enum NewsType { stock, ai }

class NewsTypeNotifier extends StateNotifier<NewsType> {
  static const _key = 'news_type';

  NewsTypeNotifier() : super(_load());

  static NewsType _load() {
    final idx = gPrefs.getInt(_key) ?? 0;
    return NewsType.values[idx.clamp(0, 1)];
  }

  void setNewsType(NewsType type) {
    state = type;
    gPrefs.setInt(_key, type.index);
  }

  void toggle() {
    final next = state == NewsType.stock ? NewsType.ai : NewsType.stock;
    setNewsType(next);
  }
}

final newsTypeProvider = StateNotifierProvider<NewsTypeNotifier, NewsType>((ref) {
  return NewsTypeNotifier();
});
