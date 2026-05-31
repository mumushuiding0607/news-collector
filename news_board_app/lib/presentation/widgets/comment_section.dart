import 'package:flutter/material.dart';

/// 评论列表组件
class CommentSection extends StatefulWidget {
  final int newsId;

  const CommentSection({super.key, required this.newsId});

  @override
  State<CommentSection> createState() => _CommentSectionState();
}

class _CommentSectionState extends State<CommentSection> {
  final _commentController = TextEditingController();
  final _comments = <_Comment>[];
  bool _isLoading = false;

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
    setState(() => _isLoading = true);
    // TODO: 调用 GET /api/comments/{widget.newsId}
    await Future.delayed(const Duration(milliseconds: 500));
    setState(() => _isLoading = false);
  }

  void _submitComment() {
    if (_commentController.text.trim().isEmpty) return;
    // TODO: 调用 POST /api/comments {news_id: widget.newsId, content: ...}
    setState(() {
      _comments.insert(0, _Comment(
        id: DateTime.now().millisecondsSinceEpoch,
        nickname: '我',
        content: _commentController.text.trim(),
        time: '刚刚',
      ));
      _commentController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('评论', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        // 输入框
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

  Widget _buildCommentItem(_Comment comment) {
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

class _Comment {
  final int id;
  final String nickname;
  final String content;
  final String time;

  _Comment({required this.id, required this.nickname, required this.content, required this.time});
}