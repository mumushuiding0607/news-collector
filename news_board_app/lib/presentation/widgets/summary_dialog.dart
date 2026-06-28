import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/config_provider.dart';
import '../../data/repositories/summary_repository.dart';

/// 简报弹窗（showGeneralDialog 方式全屏展示）
class SummaryDialog extends ConsumerStatefulWidget {
  const SummaryDialog({super.key});

  @override
  ConsumerState<SummaryDialog> createState() => _SummaryDialogState();
}

class _SummaryDialogState extends ConsumerState<SummaryDialog> {
  final _repo = SummaryRepository();
  List<SummaryItem> _items = [];
  int _total = 0;
  int _page = 1;
  int _limit = 20;
  bool _isLoading = true;
  String? _error;
  SummaryItem? _selectedItem;
  SummaryData? _selectedSummary;
  bool _loadingDetail = false;

  @override
  void initState() {
    super.initState();
    _loadList();
  }

  Future<void> _loadList() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    final result = await _repo.getSummaryList(page: _page, limit: _limit);
    if (mounted) {
      setState(() {
        _items = (result['items'] as List<SummaryItem>?) ?? [];
        _total = result['total'] as int? ?? 0;
        _isLoading = false;
        if (_items.isEmpty) _error = '暂无简报';
      });
    }
  }

  Future<void> _loadDetail(SummaryItem item) async {
    setState(() {
      _selectedItem = item;
      _loadingDetail = true;
      _selectedSummary = null;
    });
    final data = await _repo.getSummary(date: item.date, type: item.type);
    if (mounted) {
      setState(() {
        _selectedSummary = data;
        _loadingDetail = false;
      });
    }
  }

  int get _totalPages => (_total / _limit).ceil();

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF1A1A1A),
      insetPadding: EdgeInsets.zero,
      child: Container(
        width: MediaQuery.of(context).size.width,
        height: MediaQuery.of(context).size.height,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF1A1A1A), Color(0xFF141414)],
          ),
        ),
        child: SafeArea(
          child: _selectedItem != null
              ? _buildDetailView()
              : _buildListView(),
        ),
      ),
    );
  }

  // ==================== 列表页 ====================

  Widget _buildListView() {
    return Column(
      children: [
        _buildHeader(title: '简报'),
        Expanded(
          child: _isLoading
              ? const Center(child: CircularProgressIndicator(color: Colors.amber))
              : _error != null
                  ? _buildEmptyState()
                  : _buildList(),
        ),
        if (_totalPages > 1) _buildPagination(),
      ],
    );
  }

  Widget _buildHeader({required String title}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: Colors.white.withOpacity(0.06))),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, color: Colors.white54),
            onPressed: () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.summarize_outlined, color: Colors.white24, size: 56),
          const SizedBox(height: 16),
          Text(_error ?? '暂无简报', style: const TextStyle(color: Colors.white54, fontSize: 15)),
          const SizedBox(height: 20),
          TextButton(
            onPressed: _loadList,
            child: const Text('重试', style: TextStyle(color: Colors.amber)),
          ),
        ],
      ),
    );
  }

  Widget _buildList() {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      itemCount: _items.length,
      itemBuilder: (context, index) => _buildListCard(_items[index]),
    );
  }

  Widget _buildListCard(SummaryItem item) {
    return GestureDetector(
      onTap: () => _loadDetail(item),
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF252525), Color(0xFF1E1E1E)],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 12, offset: const Offset(0, 4)),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Colors.amber.shade700, Colors.amber.shade900],
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    item.date.length > 5 ? item.date.substring(5).replaceFirst('-', '/') : item.date,
                    style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.type,
                    style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    item.createdAt.isNotEmpty ? item.createdAt : item.date,
                    style: const TextStyle(color: Colors.white38, fontSize: 12),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: Colors.white38),
          ],
        ),
      ),
    );
  }

  Widget _buildPagination() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _pageButton(Icons.chevron_left, _page > 1 ? () { setState(() => _page--); _loadList(); } : null),
          const SizedBox(width: 16),
          Text('$_page / $_totalPages', style: const TextStyle(color: Colors.white70, fontSize: 14)),
          const SizedBox(width: 16),
          _pageButton(Icons.chevron_right, _page < _totalPages ? () { setState(() => _page++); _loadList(); } : null),
        ],
      ),
    );
  }

  Widget _pageButton(IconData icon, VoidCallback? onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: onTap != null ? Colors.white.withOpacity(0.08) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.white.withOpacity(0.1)),
        ),
        child: Icon(icon, color: onTap != null ? Colors.white70 : Colors.white12, size: 22),
      ),
    );
  }

  // ==================== 详情页 ====================

  Widget _buildDetailView() {
    return Column(
      children: [
        _buildHeader(title: _selectedItem?.type ?? '简报'),
        Expanded(
          child: _loadingDetail
              ? const Center(child: CircularProgressIndicator(color: Colors.amber))
              : _selectedSummary != null
                  ? _buildDetailContent(_selectedSummary!)
                  : _buildEmptyDetail(),
        ),
      ],
    );
  }

  Widget _buildEmptyDetail() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.summarize_outlined, color: Colors.white24, size: 48),
          const SizedBox(height: 16),
          const Text('暂无详情', style: TextStyle(color: Colors.white54)),
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => _loadDetail(_selectedItem!),
            child: const Text('重试', style: TextStyle(color: Colors.amber)),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailContent(SummaryData summary) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 日期标题栏
          _buildDateHeader(summary),
          const SizedBox(height: 24),
          // 今日概述
          if (summary.summary != null && summary.summary!.isNotEmpty) ...[
            _buildSection(
              label: '今日概述',
              icon: Icons.article_outlined,
              labelColor: Colors.amber,
              bgColor: Colors.white.withOpacity(0.04),
              borderColor: Colors.amber.withOpacity(0.2),
              content: summary.summary!,
            ),
            const SizedBox(height: 16),
          ],
          // 主要刺激源
          if (summary.mainStimulus != null && summary.mainStimulus!.isNotEmpty) ...[
            _buildSection(
              label: '主要刺激源',
              icon: Icons.bolt_outlined,
              labelColor: Colors.orangeAccent,
              bgColor: Colors.orangeAccent.withOpacity(0.08),
              borderColor: Colors.orangeAccent.withOpacity(0.25),
              content: summary.mainStimulus!,
            ),
            const SizedBox(height: 16),
          ],
          // 异动关联性
          if (summary.correlation != null && summary.correlation!.isNotEmpty) ...[
            _buildSection(
              label: '异动关联性',
              icon: Icons.link_outlined,
              labelColor: Colors.cyanAccent,
              bgColor: Colors.cyanAccent.withOpacity(0.08),
              borderColor: Colors.cyanAccent.withOpacity(0.25),
              content: summary.correlation!,
            ),
            const SizedBox(height: 16),
          ],
          // 对消息套利者的启发
          if (summary.insights != null && summary.insights!.isNotEmpty) ...[
            _buildSection(
              label: '对消息套利者的启发',
              icon: Icons.lightbulb_outline,
              labelColor: Colors.greenAccent,
              bgColor: Colors.greenAccent.withOpacity(0.08),
              borderColor: Colors.greenAccent.withOpacity(0.25),
              content: summary.insights!,
            ),
            const SizedBox(height: 16),
          ],
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildDateHeader(SummaryData summary) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Colors.amber.shade800.withOpacity(0.3), Colors.amber.shade900.withOpacity(0.15)],
        ),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.amber.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.amber.shade700,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              summary.date ?? '',
              style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  summary.type ?? '简报',
                  style: const TextStyle(color: Colors.amber, fontSize: 16, fontWeight: FontWeight.bold),
                ),
                if (summary.totalNews != null)
                  Text(
                    '共 ${summary.totalNews} 条异动消息',
                    style: TextStyle(color: Colors.amber.shade200, fontSize: 12),
                  ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.arrow_back, color: Colors.white54),
            onPressed: () => setState(() {
              _selectedItem = null;
              _selectedSummary = null;
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildSection({
    required String label,
    required IconData icon,
    required Color labelColor,
    required Color bgColor,
    required Color borderColor,
    String? content,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: labelColor, size: 16),
              const SizedBox(width: 7),
              Text(
                label,
                style: TextStyle(
                  color: labelColor,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (content != null)
            Text(
              content,
              style: const TextStyle(color: Colors.white70, fontSize: 14, height: 1.7),
            ),
        ],
      ),
    );
  }
}