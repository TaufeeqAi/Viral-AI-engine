// chatservice.dart
import 'package:uuid/uuid.dart'; // Ensure this is imported if you use Uuid()
import 'package:intl/intl.dart'; // For parsing ISO 8601 strings
import 'dart:convert'; // For jsonDecode if content is a string

class ChatHistory {
  final String id;
  final String sessionId;
  final String role; // 'user', 'agent', 'tool' (matches Python's 'role')
  final dynamic
  content; // MODIFIED: Changed from String to dynamic to handle Map<String, dynamic>
  final DateTime timestamp;
  final bool isPartial; // MODIFIED: Added isPartial field
  final Map<String, dynamic>? metadata;
  final List<String>? attachments;
  final String? parentMessageId; // For threading/replies

  ChatHistory({
    required this.id,
    required this.sessionId,
    required this.role,
    required this.content,
    required this.timestamp,
    this.isPartial = false, // MODIFIED: Initialize isPartial
    this.metadata,
    this.attachments,
    this.parentMessageId,
  });

  factory ChatHistory.fromJson(Map<String, dynamic> json) {
    // MODIFIED: Handle content field correctly.
    // It should now come as a Map<String, dynamic> from the Python backend
    // with a 'text' key for the actual message.
    dynamic parsedContent = json['content'];
    if (parsedContent is String) {
      // Fallback for cases where content might still be a raw string (e.g., older entries)
      // Attempt to parse as JSON, otherwise treat as plain text.
      try {
        parsedContent = jsonDecode(parsedContent);
      } catch (e) {
        parsedContent = {'text': parsedContent}; // Wrap plain string in a map
      }
    } else if (parsedContent is! Map<String, dynamic>) {
      // Ensure it's always a map, even if it's null or some other unexpected type
      parsedContent = {'text': parsedContent?.toString() ?? ''};
    }
    // Ensure 'text' key exists if it's a map, for consistent access
    if (parsedContent is Map<String, dynamic> &&
        !parsedContent.containsKey('text')) {
      parsedContent['text'] = parsedContent
          .toString(); // Use map's string representation if no 'text'
    }

    return ChatHistory(
      id: json['id'],
      sessionId: json['session_id'],
      role: json['role'], // Expect 'role' field from Python API
      content: parsedContent, // Pass the parsed content (now a Map or String)
      timestamp: DateTime.parse(json['timestamp']),
      isPartial:
          json['is_partial'] ??
          false, // MODIFIED: Parse is_partial, default to false
      metadata: json['metadata'] != null
          ? Map<String, dynamic>.from(json['metadata'])
          : null,
      attachments: json['attachments'] != null
          ? List<String>.from(json['attachments'])
          : null,
      parentMessageId: json['parent_message_id'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'session_id': sessionId,
      'role': role,
      'content': content, // Keep as dynamic for now, Python will handle it
      'timestamp': timestamp.toIso8601String(),
      'is_partial': isPartial, // MODIFIED: Include isPartial in toJson
      'metadata': metadata,
      'attachments': attachments,
      'parent_message_id': parentMessageId,
    };
  }

  // Helper to get the text content, useful for displaying messages
  String get textContent {
    if (content is Map<String, dynamic> && content.containsKey('text')) {
      return content['text'] as String;
    }
    return content.toString(); // Fallback if content is not a map with 'text'
  }
}
