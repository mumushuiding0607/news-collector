import 'package:flutter/material.dart';

class AppTheme {
  // 背景渐变色 - 微红暗色
  static const Color backgroundStart = Color(0xFF1A0808);
  static const Color backgroundEnd = Color(0xFF2A1010);

  // 强调色 - 玻璃红系
  static const Color accentRed = Color(0xFFE53935);    // 涨 / 强调
  static const Color accentRedLight = Color(0xFFFF6659);  // 浅红
  static const Color accentRedDark = Color(0xFFAB000D);   // 深红
  static const Color glassRed = Color(0x33E53935);       // 玻璃红 (20% opacity)
  static const Color glassRedBorder = Color(0x55E53935); // 玻璃红边框 (33% opacity)

  // 其它强调色
  static const Color accentGreen = Color(0xFF43A047);  // 跌
  static const Color accentGold = Color(0xFFFFB300);  // 高分

  // 文字颜色
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFB0B0B0);
  static const Color textMuted = Color(0xFF707070);

  // 卡片颜色 - 带红色调
  static const Color cardBackground = Color(0x22E53935); // 13% red tint
  static const Color cardBorder = Color(0x44E53935);    // 27% red tint

  // 渐变背景
  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [backgroundStart, backgroundEnd],
  );

  // 玻璃卡片装饰
  static BoxDecoration get glassCardDecoration => BoxDecoration(
    color: cardBackground,
    borderRadius: BorderRadius.circular(20),
    border: Border.all(color: cardBorder, width: 1),
    boxShadow: [
      BoxShadow(
        color: Colors.black.withOpacity(0.4),
        blurRadius: 20,
        offset: const Offset(0, 10),
      ),
    ],
  );

  // 玻璃红卡片装饰
  static BoxDecoration get glassRedCardDecoration => BoxDecoration(
    color: glassRed,
    borderRadius: BorderRadius.circular(20),
    border: Border.all(color: glassRedBorder, width: 1),
    boxShadow: [
      BoxShadow(
        color: accentRed.withOpacity(0.3),
        blurRadius: 20,
        offset: const Offset(0, 10),
      ),
    ],
  );

  // 评分颜色
  static Color getScoreColor(int score) {
    if (score >= 9) return accentRed;
    if (score >= 7) return accentGold;
    return Colors.grey;
  }

  // 涨跌颜色
  static Color getChangeColor(double change) {
    if (change > 0) return accentRed;
    if (change < 0) return accentGreen;
    return textMuted;
  }

  // AppBar 主题
  static AppBarTheme get appBarTheme => const AppBarTheme(
    backgroundColor: Colors.transparent,
    elevation: 0,
    centerTitle: true,
    titleTextStyle: TextStyle(
      color: textPrimary,
      fontSize: 20,
      fontWeight: FontWeight.bold,
    ),
    iconTheme: IconThemeData(color: textPrimary),
  );

  // 深色主题 - 主色为红色
  static ThemeData get darkTheme => ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: backgroundStart,
    primaryColor: accentRed,
    appBarTheme: appBarTheme,
    colorScheme: const ColorScheme.dark(
      primary: accentRed,
      secondary: accentGold,
      surface: backgroundStart,
      onPrimary: Colors.white,
      onSecondary: Colors.black,
      onSurface: textPrimary,
    ),
    textTheme: const TextTheme(
      headlineLarge: TextStyle(
        color: textPrimary,
        fontSize: 28,
        fontWeight: FontWeight.bold,
      ),
      headlineMedium: TextStyle(
        color: textPrimary,
        fontSize: 22,
        fontWeight: FontWeight.bold,
      ),
      titleLarge: TextStyle(
        color: textPrimary,
        fontSize: 18,
        fontWeight: FontWeight.w600,
      ),
      titleMedium: TextStyle(
        color: textPrimary,
        fontSize: 16,
        fontWeight: FontWeight.w500,
      ),
      bodyLarge: TextStyle(
        color: textPrimary,
        fontSize: 16,
      ),
      bodyMedium: TextStyle(
        color: textSecondary,
        fontSize: 14,
      ),
      bodySmall: TextStyle(
        color: textMuted,
        fontSize: 12,
      ),
    ),
  );
}