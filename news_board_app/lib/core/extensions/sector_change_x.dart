/// 板块涨跌计算扩展方法，替代散落在 news_card_content、news_card_sectors、news_detail_sector_section 的重复代码
extension SectorChangeX on double {
  String get changeText {
    if (this >= 0) {
      return '+${toStringAsFixed(2)}%';
    }
    return '${toStringAsFixed(2)}%';
  }

  int get changeLevel {
    if (this >= 5) return 3;
    if (this >= 2) return 2;
    if (this > 0) return 1;
    if (this == 0) return 0;
    if (this >= -2) return -1;
    if (this >= -5) return -2;
    return -3;
  }
}

/// 计算涨跌百分比（替代多处重复的 _getChange / _calcPct）
double calcPct(double change, double prev) {
  if (prev == 0) return 0;
  return (change - prev) / prev * 100;
}