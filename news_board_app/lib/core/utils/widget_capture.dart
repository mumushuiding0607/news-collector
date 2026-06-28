import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

/// 通用 widget 截图工具
///
/// 使用 Overlay 在屏幕外渲染指定 widget 并截取为 PNG 图片字节。
/// 特点：
/// - 通用性强：任意 widget 都可截图
/// - 不影响 UI：截取过程对用户不可见
/// - 内容独立：截图内容由调用方传入，与调用页面解耦
///
/// 注意：Web 平台暂不支持（RenderRepaintBoundary.toImage 在 Web 上不可用）
class WidgetCapture {
  /// 在屏幕外渲染并截取 widget 为 PNG 字节
  ///
  /// [context] 用于获取 Overlay，必须是已挂载的 BuildContext
  /// [builder] 构建要截图的 widget
  /// [pixelRatio] 像素密度，越大越清晰，默认 2.5
  /// [delay] 渲染等待时间，默认 100ms
  ///
  /// 返回 PNG 字节，失败时返回 null
  static Future<Uint8List?> capture({
    required BuildContext context,
    required WidgetBuilder builder,
    double pixelRatio = 2.5,
    Duration delay = const Duration(milliseconds: 100),
  }) async {
    // Web 平台暂不支持 toImage
    if (kIsWeb) {
      debugPrint('WidgetCapture: not supported on Web platform');
      return null;
    }

    final repaintKey = GlobalKey();
    final overlay = Overlay.maybeOf(context, rootOverlay: true);
    if (overlay == null) {
      debugPrint('WidgetCapture: Overlay not found');
      return null;
    }

    // 在屏幕外插入 widget 树
    // 使用 IgnorePointer 避免触发 MouseTracker 断言
    final entry = OverlayEntry(
      builder: (ctx) => Positioned(
        left: -10000,
        top: -10000,
        child: IgnorePointer(
          child: Material(
            type: MaterialType.transparency,
            child: RepaintBoundary(
              key: repaintKey,
              child: Builder(builder: builder),
            ),
          ),
        ),
      ),
    );

    overlay.insert(entry);

    try {
      // 等待渲染完成
      await WidgetsBinding.instance.endOfFrame;
      if (delay > Duration.zero) {
        await Future.delayed(delay);
      }

      final boundary = repaintKey.currentContext?.findRenderObject()
          as RenderRepaintBoundary?;
      if (boundary == null) {
        debugPrint('WidgetCapture: RepaintBoundary not found');
        return null;
      }

      final image = await boundary.toImage(pixelRatio: pixelRatio);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      image.dispose();
      return byteData?.buffer.asUint8List();
    } catch (e, st) {
      debugPrint('WidgetCapture error: $e\n$st');
      return null;
    } finally {
      entry.remove();
    }
  }
}
