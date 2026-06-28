import '../../core/utils/api_client.dart';

/// 简报列表项
class SummaryItem {
  final String date;
  final String type;
  final String createdAt;

  const SummaryItem({
    required this.date,
    required this.type,
    required this.createdAt,
  });

  factory SummaryItem.fromJson(Map<String, dynamic> json) {
    return SummaryItem(
      date: json['date'] as String? ?? '',
      type: json['type'] as String? ?? '简报',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

/// 简报数据模型
class SummaryData {
  final String? type;
  final String? date;
  final String? summary;
  final String? mainStimulus;
  final String? correlation;
  final String? insights;
  final int? totalNews;

  const SummaryData({
    this.type,
    this.date,
    this.summary,
    this.mainStimulus,
    this.correlation,
    this.insights,
    this.totalNews,
  });

  factory SummaryData.fromJson(Map<String, dynamic> json) {
    return SummaryData(
      type: json['type'] as String?,
      date: json['date'] as String?,
      summary: json['summary'] as String?,
      mainStimulus: json['main_stimulus'] as String?,
      correlation: json['correlation'] as String?,
      insights: json['insights'] as String?,
      totalNews: json['total_news'] as int?,
    );
  }
}

/// 简报 Repository
class SummaryRepository {
  /// 获取简报内容
  /// - 不传 date/type：返回最新一条
  /// - 传 date+type：返回指定条目
  Future<SummaryData?> getSummary({String? date, String? type}) async {
    try {
      final params = <String, String>{};
      if (date != null) params['date'] = date;
      if (type != null) params['type'] = type;
      final qs = params.isEmpty ? '' : '?${Uri(queryParameters: params).query}';
      final data = await ApiClient.get("/api/news/summary$qs");
      final summaryData = data['data'];
      if (summaryData == null) return null;
      return SummaryData.fromJson(summaryData as Map<String, dynamic>);
    } catch (e) {
      return null;
    }
  }

  /// 获取简报列表
  Future<Map<String, dynamic>> getSummaryList({int page = 1, int limit = 20}) async {
    try {
      final data = await ApiClient.get("/api/news/summary/list?page=$page&limit=$limit");
      final items = (data['items'] as List<dynamic>?)
              ?.map((e) => SummaryItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];
      return {
        "items": items,
        "total": data['total'] as int? ?? 0,
        "page": data['page'] as int? ?? page,
        "limit": data['limit'] as int? ?? limit,
      };
    } catch (e) {
      return {"items": <SummaryItem>[], "total": 0, "page": page, "limit": limit};
    }
  }
}