/// 统一错误格式化，替代散落的 e.toString().replaceFirst('Exception: ', '')
String formatError(Object error) {
  return error.toString().replaceFirst('Exception: ', '');
}