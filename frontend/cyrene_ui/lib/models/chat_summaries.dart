// chat_summary.dart - Summaries for sessions
class ChatSummary {
  final String id;
  final String sessionId;
  final String summary;
  final List<String> keywords;
  final String sentiment; // 'positive', 'negative', 'neutral'
  final int messageCount;
  final DateTime createdAt;
  final DateTime updatedAt;

  ChatSummary({
    required this.id,
    required this.sessionId,
    required this.summary,
    required this.keywords,
    required this.sentiment,
    required this.messageCount,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ChatSummary.fromJson(Map<String, dynamic> json) {
    return ChatSummary(
      id: json['id'],
      sessionId: json['session_id'],
      summary: json['summary'],
      keywords: List<String>.from(json['keywords']),
      sentiment: json['sentiment'],
      messageCount: json['message_count'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'session_id': sessionId,
      'summary': summary,
      'keywords': keywords,
      'sentiment': sentiment,
      'message_count': messageCount,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}
