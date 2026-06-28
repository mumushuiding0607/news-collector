import 'package:flutter/material.dart';
import '../../data/repositories/comment_repository.dart';
import '../../data/repositories/token_manager.dart';

/// 评论列表组件
class CommentSection extends StatefulWidget {
  final int newsId;

  const CommentSection({super.key, required this.newsId});

  @override
  State<CommentSection> createState() => _CommentSectionState();
}

class _CommentItem {
  final int id;
  final String nickname;
  final String content;
  final String time;

  _CommentItem({required this.id, required this.nickname, required this.content, required this.time});

  factory _CommentItem.fromJson(Map<String, dynamic> json) {
    return _CommentItem(
      id: json['id'] as int? ?? 0,
      nickname: json['display_name'] as String? ?? json['nickname'] as String? ?? '匿名用户',
      content: json['content'] as String? ?? '',
      time: json['created_at'] as String? ?? '',
    );
  }
}

class _CommentSectionState extends State<CommentSection> {
  final _commentController = TextEditingController();
  final _repo = CommentRepository();
  final _comments = <_CommentItem>[];
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadComments();
  }

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _loadComments() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final raw = await _repo.getComments(widget.newsId);
      setState(() {
        _comments.clear();
        _comments.addAll(raw.map((e) => _CommentItem.fromJson(e)));
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _submitComment() async {
    final text = _commentController.text.trim();
    if (text.isEmpty) return;

    final token = await TokenManager.getToken();
    if (token == null) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          content: const Text('请先登录'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('确定')),
          ],
        ),
      );
      return;
    }

    await _repo.addComment(widget.newsId, text);
    _commentController.clear();
    await _loadComments();
    if (mounted) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          content: const Text('评论成功'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('确定')),
          ],
        ),
      );
    }
    // 错误已由 ApiClient 弹窗提示
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('评论', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _commentController,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: '写下你的评论...',
                  hintStyle: const TextStyle(color: Colors.white30),
                  filled: true,
                  fillColor: Colors.white.withOpacity(0.05),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(20), borderSide: BorderSide.none),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              onPressed: _submitComment,
              icon: const Icon(Icons.send, color: Colors.amber),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_isLoading)
          const Center(child: CircularProgressIndicator(strokeWidth: 2, color: Colors.amber))
        else if (_errorMessage != null)
          Center(
            child: Text(_errorMessage!, style: const TextStyle(color: Colors.red, fontSize: 12)),
          )
        else if (_comments.isEmpty)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(20),
              child: Text('暂无评论', style: TextStyle(color: Colors.white38)),
            ),
          )
        else
          ..._comments.map(_buildCommentItem),
      ],
    );
  }

  Widget _buildCommentItem(_CommentItem comment) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 14,
                backgroundColor: Colors.amber.withOpacity(0.3),
                child: Text(comment.nickname[0], style: const TextStyle(color: Colors.amber, fontSize: 12)),
              ),
              const SizedBox(width: 8),
              Text(comment.nickname, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
              const Spacer(),
              Text(comment.time, style: const TextStyle(color: Colors.white38, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 8),
          Text(comment.content, style: const TextStyle(color: Colors.white70, fontSize: 14)),
        ],
      ),
    );
  }
}
