class NewsItem {
  final int id;
  final String title;
  final String url;
  final String sourceName;
  final String publishTime;
  final String summary;
  final String relatedSectors;
  final int importanceScore;
  final String reason;
  final String? direction;
  final int? intensity;
  final String? expectedChange;
  final String? duration;
  final String? expectationLevel;
  final String? marketMode;
  final double? maxSectorRise;
  final String publishSectorValues;
  final String? currentSectorValues;
  final String? currentSectorChangeRates;
  final String createdAt;
  final List<CoreStockPreview> coreStocksPreview;

  NewsItem({
    required this.id,
    required this.title,
    required this.url,
    required this.sourceName,
    required this.publishTime,
    required this.summary,
    required this.relatedSectors,
    required this.importanceScore,
    required this.reason,
    this.direction,
    this.intensity,
    this.expectedChange,
    this.duration,
    this.expectationLevel,
    this.marketMode,
    this.maxSectorRise,
    required this.publishSectorValues,
    this.currentSectorValues,
    this.currentSectorChangeRates,
    required this.createdAt,
    this.coreStocksPreview = const [],
  });

  factory NewsItem.fromJson(Map<String, dynamic> json) {
    return NewsItem(
      id: json['id'] as int,
      title: json['title'] as String? ?? '',
      url: json['url'] as String? ?? '',
      sourceName: json['source_name'] as String? ?? '',
      publishTime: json['publish_time'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
      relatedSectors: json['related_sectors'] as String? ?? '',
      importanceScore: (json['importance_score'] as num?)?.toInt() ?? 0,
      reason: json['reason'] as String? ?? '',
      direction: json['direction'] as String?,
      intensity: (json['intensity'] as num?)?.toInt(),
      expectedChange: json['expected_change'] as String?,
      duration: json['duration'] as String?,
      expectationLevel: json['expectation_level'] as String?,
      marketMode: json['market_mode'] as String?,
      maxSectorRise: (json['max_sector_rise'] as num?)?.toDouble(),
      publishSectorValues: json['publish_sector_values'] as String? ?? '',
      currentSectorValues: json['current_sector_values'] as String?,
      currentSectorChangeRates: json['current_sector_change_rates'] as String?,
      createdAt: json['created_at'] as String? ?? '',
      coreStocksPreview: (json['core_stocks_preview'] as List<dynamic>?)
          ?.map((e) => CoreStockPreview.fromJson(e as Map<String, dynamic>))
          .toList() ?? [],
    );
  }

  /// 解析板块名称列表
  List<String> get sectorList {
    if (relatedSectors.isEmpty) return [];
    return relatedSectors.split('|').where((s) => s.trim().isNotEmpty).toList();
  }

  /// 解析发布时板块指数
  Map<String, double> get publishSectorMap {
    return _parseSectorValues(publishSectorValues);
  }

  /// 解析当前板块指数
  Map<String, double> get currentSectorMap {
    if (currentSectorValues == null || currentSectorValues!.isEmpty) {
      return publishSectorMap;
    }
    return _parseSectorValues(currentSectorValues!);
  }

  /// 解析当前板块涨跌幅列表（按 relatedSectors 顺序，只存值）
  List<double> get currentChangeRateList {
    return _parseChangeRates(currentSectorChangeRates ?? '');
  }

  Map<String, double> _parseSectorValues(String values) {
    final map = <String, double>{};
    if (values.isEmpty) return map;
    for (final part in values.split('|')) {
      final segments = part.split(':');
      if (segments.length >= 2) {
        final name = segments[0].trim();
        final value = double.tryParse(segments[1]) ?? 0;
        map[name] = value;
      }
    }
    return map;
  }

  /// 解析板块涨跌幅列表（格式: "涨跌幅|涨跌幅"，按 relatedSectors 顺序）
  List<double> _parseChangeRates(String values) {
    final list = <double>[];
    if (values.isEmpty) return list;
    for (final part in values.split('|')) {
      final rateStr = part.trim().replaceAll('%', '');
      final rate = double.tryParse(rateStr) ?? 0;
      list.add(rate);
    }
    return list;
  }

  /// 计算板块指数变化（发布至今）
  List<SectorChange> get sectorChanges {
    final changes = <SectorChange>[];
    final publishMap = publishSectorMap;
    final currentMap = currentSectorMap;

    for (final entry in publishMap.entries) {
      final currentValue = currentMap[entry.key] ?? entry.value;
      final change = currentValue - entry.value;
      changes.add(SectorChange(
        name: entry.key,
        publishValue: entry.value,
        currentValue: currentValue,
        change: change,
      ));
    }

    return changes;
  }

  /// 总变化值
  double get totalChange {
    return sectorChanges.fold(0, (sum, c) => sum + c.change);
  }
}

class CoreStockPreview {
  final String sector;
  final String name;
  final String tier;
  final String? chainLink;
  final Map<String, dynamic>? fourDims;
  final String? moat;
  final String? d1;  // 发布当天收盘涨跌幅
  final String? d2;  // 发布后第1天涨跌幅
  final String? d3;  // 发布后第2天涨跌幅

  CoreStockPreview({
    required this.sector,
    required this.name,
    required this.tier,
    this.chainLink,
    this.fourDims,
    this.moat,
    this.d1,
    this.d2,
    this.d3,
  });

  bool get hasFullData => chainLink != null || fourDims != null || moat != null;

  /// 是否有三日涨跌数据
  bool get hasPriceChange => d1 != null || d2 != null || d3 != null;

  factory CoreStockPreview.fromJson(Map<String, dynamic> json) {
    return CoreStockPreview(
      sector: json['sector'] as String? ?? '',
      name: json['name'] as String? ?? '',
      tier: json['tier'] as String? ?? '',
      chainLink: json['chain_link'] as String?,
      fourDims: json['four_dims'] as Map<String, dynamic>?,
      moat: json['moat'] as String?,
      d1: json['d1'] as String?,
      d2: json['d2'] as String?,
      d3: json['d3'] as String?,
    );
  }
}

/// 核心标的完整信息（用于详情弹窗）
class CoreStockDetail {
  final String sector;
  final String name;
  final String tier;
  final String? chainLink;       // 护城河
  final Map<String, dynamic>? fourDims;  // 四维度
  final String? moat;           // 核心逻辑
  final String? q1Metrics;      // 一季度指标

  const CoreStockDetail({
    required this.sector,
    required this.name,
    required this.tier,
    this.chainLink,
    this.fourDims,
    this.moat,
    this.q1Metrics,
  });

  factory CoreStockDetail.fromJson(Map<String, dynamic> json) {
    return CoreStockDetail(
      sector: json['sector'] as String? ?? '',
      name: json['name'] as String? ?? '',
      tier: json['tier'] as String? ?? '',
      chainLink: json['chain_link'] as String?,
      fourDims: json['four_dims'] as Map<String, dynamic>?,
      moat: json['moat'] as String?,
      q1Metrics: json['q1_metrics'] as String?,
    );
  }

  /// 从 CoreStockPreview 转换（用于预览）
  factory CoreStockDetail.fromPreview(CoreStockPreview p) {
    return CoreStockDetail(sector: p.sector, name: p.name, tier: p.tier);
  }
}

class SectorChange {
  final String name;
  final double publishValue;
  final double currentValue;
  final double change;

  SectorChange({
    required this.name,
    required this.publishValue,
    required this.currentValue,
    required this.change,
  });
}