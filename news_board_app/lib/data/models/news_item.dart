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
  final String publishSectorValues;
  final String? currentSectorValues;
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
    required this.publishSectorValues,
    this.currentSectorValues,
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
      importanceScore: json['importance_score'] as int? ?? 0,
      reason: json['reason'] as String? ?? '',
      publishSectorValues: json['publish_sector_values'] as String? ?? '',
      currentSectorValues: json['current_sector_values'] as String?,
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

  /// 计算板块指数变化
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

  CoreStockPreview({
    required this.sector,
    required this.name,
    required this.tier,
    this.chainLink,
    this.fourDims,
    this.moat,
  });

  bool get hasFullData => chainLink != null || fourDims != null || moat != null;

  factory CoreStockPreview.fromJson(Map<String, dynamic> json) {
    return CoreStockPreview(
      sector: json['sector'] as String? ?? '',
      name: json['name'] as String? ?? '',
      tier: json['tier'] as String? ?? '',
      chainLink: json['chain_link'] as String?,
      fourDims: json['four_dims'] as Map<String, dynamic>?,
      moat: json['moat'] as String?,
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