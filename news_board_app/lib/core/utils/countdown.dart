import 'dart:async';

/// 倒计时控制器，可多处复用
class CountdownController {
  int _countdown = 0;
  bool _isRunning = false;
  final void Function(int) onTick;
  final void Function()? onComplete;

  CountdownController({
    required this.onTick,
    this.onComplete,
  });

  int get countdown => _countdown;
  bool get isRunning => _isRunning;

  void start(int seconds) {
    _countdown = seconds;
    _isRunning = true;
    onTick(_countdown);
    _tick();
  }

  void _tick() {
    Future.delayed(const Duration(seconds: 1), () {
      if (_countdown > 0 && _isRunning) {
        _countdown--;
        onTick(_countdown);
        _tick();
      } else if (_isRunning) {
        _isRunning = false;
        onComplete?.call();
      }
    });
  }

  void stop() {
    _isRunning = false;
    _countdown = 0;
  }
}

/// 内联倒计时辅助函数（替代多处重复的 _startCountdown）
void runCountdown({
  required int seconds,
  required void Function(int) onTick,
  void Function()? onComplete,
}) {
  int remaining = seconds;
  onTick(remaining);
  Future.doWhile(() async {
    await Future.delayed(const Duration(seconds: 1));
    if (remaining > 0) {
      remaining--;
      onTick(remaining);
      return true;
    }
    onComplete?.call();
    return false;
  });
}