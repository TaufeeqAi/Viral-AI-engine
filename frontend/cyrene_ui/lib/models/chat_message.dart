// frontend/cyrene_ui/lib/models/chat_message.dart
import 'package:uuid/uuid.dart'; // Ensure this is imported for generating unique IDs
import 'dart:convert'; // MODIFIED: Added for jsonDecode

// Define MessageType enum if it's not already defined in this file
enum MessageType { user, agent, system, error }

class ChatMessage {
  final String id;
  final String sessionId;
  final String role; // 'user', 'agent', 'tool' (matches Python's 'role')
  final dynamic
  content; // MODIFIED: Changed from String to dynamic to handle Map<String, dynamic>
  final MessageType
  type; // Used for UI display logic (user, agent, system, error)
  final DateTime timestamp;
  final bool isLoading;
  final bool isPartial;
  final Map<String, dynamic>? metadata;

  ChatMessage({
    required this.id,
    required this.sessionId,
    required this.role,
    required this.content,
    required this.type,
    required this.timestamp,
    this.isLoading = false,
    this.isPartial = false,
    this.metadata,
  });

  // Factory constructor for user messages
  factory ChatMessage.user(String content) {
    return ChatMessage(
      id: const Uuid().v4(), // Generate a unique ID
      sessionId:
          '', // Session ID will be set when sent to backend or received from history
      role: 'user', // Explicit role for user messages
      content: {'text': content}, // MODIFIED: Wrap user content in a map
      type: MessageType.user,
      timestamp: DateTime.now(),
      isLoading: false,
      isPartial: false,
    );
  }

  // Factory constructor for agent messages
  factory ChatMessage.agent(String content) {
    return ChatMessage(
      id: const Uuid().v4(), // Generate a unique ID
      sessionId: '', // Session ID will be set when received from history
      role: 'agent', // Explicit role for agent messages
      content: {'text': content}, // MODIFIED: Wrap agent content in a map
      type: MessageType.agent,
      timestamp: DateTime.now(),
      isLoading: false,
      isPartial: false,
    );
  }

  // Factory constructor for error messages
  factory ChatMessage.error(String content) {
    return ChatMessage(
      id: const Uuid().v4(), // Generate a unique ID
      sessionId:
          '', // Session ID not directly relevant for a standalone error message
      role: 'system', // Error messages can be considered system messages
      content: {'text': content}, // MODIFIED: Wrap error content in a map
      type: MessageType.error,
      timestamp: DateTime.now(),
      isLoading: false,
      isPartial: false,
    );
  }

  // Factory constructor for a loading indicator message
  factory ChatMessage.loading() {
    return ChatMessage(
      id: 'loading', // A special, non-unique ID for a temporary loading message
      sessionId: '', // Not tied to a specific session ID for display purposes
      role: 'agent', // Loading is typically for an agent response
      content: {'text': ''}, // MODIFIED: Empty content as a map
      type: MessageType.agent,
      timestamp: DateTime.now(),
      isLoading: true,
      isPartial: true, // A loading message is inherently partial/in-progress
    );
  }

  // Factory constructor to create a ChatMessage from a backend chat history JSON
  factory ChatMessage.fromChatHistory(Map<String, dynamic> json) {
    final String roleString = json['role'] as String;

    // MODIFIED: Handle content parsing from dynamic to Map<String, dynamic>
    dynamic rawContent = json['content'];
    Map<String, dynamic> parsedContentMap;

    if (rawContent is String) {
      // If backend sends content as a plain string (e.g., from older entries or direct DB reads)
      try {
        parsedContentMap = jsonDecode(rawContent) as Map<String, dynamic>;
      } catch (e) {
        // If it's not valid JSON, treat it as plain text
        parsedContentMap = {'text': rawContent};
      }
    } else if (rawContent is Map<String, dynamic>) {
      parsedContentMap = rawContent;
    } else {
      // Fallback for any other unexpected content type
      parsedContentMap = {'text': rawContent?.toString() ?? ''};
    }

    // Ensure 'text' key exists for consistent access
    if (!parsedContentMap.containsKey('text')) {
      parsedContentMap['text'] = parsedContentMap
          .toString(); // Use map's string representation if no 'text'
    }

    MessageType messageType;
    switch (roleString) {
      case 'user':
        messageType = MessageType.user;
        break;
      case 'agent': // MODIFIED: Directly handle 'agent' role from backend
        messageType = MessageType.agent;
        break;
      case 'tool': // NEW: Handle 'tool' role if your UI needs to display tool messages differently
        messageType =
            MessageType.system; // Or create a MessageType.tool if needed
        break;
      case 'system':
        messageType = MessageType.system;
        break;
      default:
        messageType = MessageType.system; // Default for any unhandled roles
    }

    return ChatMessage(
      id: json['id'] as String,
      sessionId: json['session_id'] as String, // Parse session_id from backend
      role: roleString, // Keep the original role string from backend
      content: parsedContentMap, // MODIFIED: Use the parsed content map
      type: messageType, // Derive MessageType for UI logic
      timestamp: DateTime.parse(json['timestamp'] as String),
      isLoading: false, // Messages from history are generally not loading
      isPartial:
          json['is_partial'] as bool? ??
          false, // Parse is_partial, default to false
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  // Helper to get the text content, useful for displaying messages
  String get textContent {
    if (content is Map<String, dynamic> && content.containsKey('text')) {
      return content['text'] as String;
    }
    return content.toString(); // Fallback if content is not a map with 'text'
  }

  // Method to create a new ChatMessage instance with updated properties
  ChatMessage copyWith({
    String? id,
    String? sessionId,
    String? role,
    dynamic content, // MODIFIED: dynamic for content
    MessageType? type,
    DateTime? timestamp,
    bool? isLoading,
    bool? isPartial,
    Map<String, dynamic>? metadata,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      sessionId: sessionId ?? this.sessionId,
      role: role ?? this.role,
      content: content ?? this.content,
      type: type ?? this.type,
      timestamp: timestamp ?? this.timestamp,
      isLoading: isLoading ?? this.isLoading,
      isPartial: isPartial ?? this.isPartial,
      metadata: metadata ?? this.metadata,
    );
  }
}
