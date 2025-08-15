// chatservice.dart
import 'package:cyrene_ui/config/app_config.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:rxdart/rxdart.dart'; // For BehaviorSubject
import 'package:flutter/foundation.dart'; // For debugPrint
import 'package:flutter/material.dart'; // For ChangeNotifier

import 'package:cyrene_ui/models/agent_config.dart';
import 'package:cyrene_ui/models/chat_summaries.dart';
import '../models/chat_session.dart';
import '../models/chat_message.dart'; // Ensure ChatMessage has 'isPartial' field

class ChatService extends ChangeNotifier {
  final String _token;
  final String _baseUrl = AppConfig.fastApiBotUrl;
  final String _wsBaseUrl = AppConfig.fastApiWsUrl;

  WebSocketChannel? _channel;
  late BehaviorSubject<ChatMessage> _messageStreamController;

  ChatService(this._token) {
    debugPrint(
      '🚀 [ChatService] Initializing ChatService with token: ${_token.isNotEmpty ? "EXISTS" : "NULL"}',
    );
    _messageStreamController = BehaviorSubject<ChatMessage>();
  }

  Map<String, String> get _headers => {
    'Authorization': 'Bearer $_token',
    'Content-Type': 'application/json',
  };

  Stream<ChatMessage> get messages => _messageStreamController.stream;

  /// Connects to the WebSocket for a specific chat session.
  /// This should be called once when a chat session is opened.
  Future<void> connectChatWebSocket(String sessionId) async {
    debugPrint(
      '🔌 [ChatService] Attempting to connect WebSocket for session: $sessionId',
    );
    // Close existing channel if any to ensure only one active connection per session
    if (_channel != null) {
      debugPrint('🔌 [ChatService] Closing existing WebSocket channel.');
      await _channel!.sink.close();
      _channel = null;
      // Re-initialize the stream controller if it was closed with the old channel
      if (_messageStreamController.isClosed) {
        debugPrint(
          '🔌 [ChatService] Re-initializing message stream controller.',
        );
        _messageStreamController = BehaviorSubject<ChatMessage>();
      }
    }

    // Construct the WebSocket URI with session ID and token
    final wsUri = Uri.parse('$_wsBaseUrl/ws/chat/$sessionId?token=$_token');
    debugPrint('🔌 [ChatService] WebSocket URI: $wsUri');
    try {
      _channel = WebSocketChannel.connect(wsUri);
      debugPrint('🔌 [ChatService] Connected to WebSocket: $wsUri');

      _channel!.stream.listen(
        (data) {
          try {
            final Map<String, dynamic> event = jsonDecode(data);
            debugPrint(
              '⬅️ [ChatService WS] Received event: ${event.toString().length > 100 ? event.toString().substring(0, 100) + '...' : event}',
            );

            final String eventType = event['type'];
            final Map<String, dynamic> payload = event['payload'];

            switch (eventType) {
              case 'session_created':
                debugPrint(
                  '✅ [ChatService WS] Session Created Event Received: ${payload.toString().length > 100 ? payload.toString().substring(0, 100) + '...' : payload}',
                );
                break;
              case 'message_created':
                final message = ChatMessage.fromChatHistory(payload);
                _messageStreamController.add(message);
                debugPrint(
                  '✅ [ChatService WS] Full Message Received: ${message.content.length > 100 ? message.content.substring(0, 100) + '...' : message.content}',
                );
                break;
              case 'llm_stream_chunk':
                final message = ChatMessage.fromChatHistory(payload);
                _messageStreamController.add(message);
                debugPrint(
                  '➡️ [ChatService WS] LLM Stream Chunk Received: ${message.content.length > 100 ? message.content.substring(0, 100) + '...' : message.content}',
                );
                break;
              case 'session_updated':
                debugPrint(
                  '🔄 [ChatService WS] Session Updated Event Received: ${payload.toString().length > 100 ? payload.toString().substring(0, 100) + '...' : payload}',
                );
                break;
              default:
                debugPrint(
                  '❓ [ChatService WS] Unknown event type: $eventType. Payload: ${payload.toString().length > 100 ? payload.toString().substring(0, 100) + '...' : payload}',
                );
            }
          } catch (e) {
            debugPrint(
              '❌ [ChatService WS] Error decoding or processing WS message: $e, Data: ${data.toString().length > 100 ? data.toString().substring(0, 100) + '...' : data}',
            );
          }
        },
        onError: (error) {
          debugPrint(
            '❌ [ChatService WS] WebSocket Error for session $sessionId: $error',
          );
          _messageStreamController.addError(
            error,
          ); // Propagate error to listeners
          _channel?.sink.close(); // Attempt to close channel on error
        },
        onDone: () {
          debugPrint(
            '🔌 [ChatService WS] WebSocket Disconnected for session $sessionId.',
          );
          _channel = null;
        },
        cancelOnError: true, // Stop listening if an error occurs
      );
    } catch (e) {
      debugPrint(
        '❌ [ChatService] Failed to connect to WebSocket for session $sessionId: $e',
      );
      rethrow; // Re-throw to inform the caller (e.g., ChatScreen)
    }
  }

  /// Disconnects the WebSocket.
  void disconnectChatWebSocket() {
    debugPrint('🔌 [ChatService] Disconnecting WebSocket...');
    _channel?.sink.close();
    _channel = null;
  }

  // ==================== CHAT SESSIONS ====================

  /// Create a new chat session
  Future<ChatSession> createChatSession({
    required String userId,
    required String agentId,
    required String title,
  }) async {
    final url = '$_baseUrl/agents/chat/sessions';
    final body = {'user_id': userId, 'agent_id': agentId, 'title': title};
    debugPrint(
      '⬆️ [ChatService] Creating chat session. URL: $url, Body: ${jsonEncode(body)}',
    );

    final response = await http.post(
      Uri.parse(url),
      headers: _headers,
      body: jsonEncode(body),
    );

    debugPrint(
      '⬇️ [ChatService] Create chat session response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Create chat session response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
      debugPrint('✅ [ChatService] Chat session created successfully.');
      return ChatSession.fromJson(jsonDecode(response.body));
    } else {
      debugPrint('❌ [ChatService] Failed to create chat session.');
      throw Exception(
        'Failed to create chat session: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Get all chat sessions for the current user
  Future<List<ChatSession>> getAllChatSessions({
    int? limit,
    String? agentId,
    bool activeOnly = true,
  }) async {
    final queryParams = <String, String>{};
    if (limit != null) queryParams['limit'] = limit.toString();
    if (agentId != null) queryParams['agent_id'] = agentId;
    if (activeOnly) queryParams['active_only'] = 'true';

    final uri = Uri.parse(
      '$_baseUrl/agents/chat/sessions',
    ).replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);
    debugPrint('⬆️ [ChatService] Getting all chat sessions. URL: $uri');

    final response = await http.get(uri, headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Get all chat sessions response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Get all chat sessions response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] All chat sessions fetched successfully.');
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => ChatSession.fromJson(json)).toList();
    } else {
      debugPrint('❌ [ChatService] Failed to get chat sessions.');
      throw Exception(
        'Failed to get chat sessions: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Get a specific chat session
  Future<ChatSession> getChatSession(String sessionId) async {
    final url = '$_baseUrl/agents/chat/sessions/$sessionId';
    debugPrint('⬆️ [ChatService] Getting chat session. URL: $url');

    final response = await http.get(Uri.parse(url), headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Get chat session response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Get chat session response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] Chat session fetched successfully.');
      return ChatSession.fromJson(jsonDecode(response.body));
    } else {
      debugPrint('❌ [ChatService] Failed to get chat session.');
      throw Exception(
        'Failed to get chat session: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Update a chat session (e.g., rename)
  Future<void> updateChatSession(
    String sessionId, {
    String? title,
    bool? isActive,
  }) async {
    final url = '$_baseUrl/agents/chat/sessions/$sessionId';
    final body = <String, dynamic>{};
    if (title != null) body['title'] = title;
    if (isActive != null) body['is_active'] = isActive;
    debugPrint(
      '⬆️ [ChatService] Updating chat session. URL: $url, Body: ${jsonEncode(body)}',
    );

    final response = await http.put(
      Uri.parse(url),
      headers: _headers,
      body: jsonEncode(body),
    );

    debugPrint(
      '⬇️ [ChatService] Update chat session response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Update chat session response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode != 204) {
      debugPrint('❌ [ChatService] Failed to update chat session.');
      throw Exception(
        'Failed to update chat session: ${response.statusCode} - ${response.body}',
      );
    } else {
      debugPrint(
        '✅ [ChatService] Chat session updated successfully (204 No Content).',
      );
    }
  }

  /// Delete a chat session
  Future<void> deleteChatSession(String sessionId) async {
    final url = '$_baseUrl/agents/chat/sessions/$sessionId';
    debugPrint('⬆️ [ChatService] Deleting chat session. URL: $url');

    final response = await http.delete(Uri.parse(url), headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Delete chat session response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Delete chat session response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode != 204) {
      debugPrint('❌ [ChatService] Failed to delete chat session.');
      throw Exception(
        'Failed to delete chat session: ${response.statusCode} - ${response.body}',
      );
    } else {
      debugPrint(
        '✅ [ChatService] Chat session deleted successfully (204 No Content).',
      );
    }
  }

  // ==================== CHAT HISTORY ====================

  /// Get chat history for a session
  Future<List<ChatMessage>> getChatSessionHistory(String sessionId) async {
    final url = '$_baseUrl/agents/chat/sessions/$sessionId/messages';
    debugPrint('⬆️ [ChatService] Getting chat history. URL: $url');

    final response = await http.get(Uri.parse(url), headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Get chat history response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Get chat history response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] Chat history fetched successfully.');
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => ChatMessage.fromChatHistory(json)).toList();
    } else {
      debugPrint('❌ [ChatService] Failed to get chat history.');
      throw Exception(
        'Failed to get chat history: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Send a message in a chat session (triggers streaming response via WebSocket)
  /// This method now just sends the user's message to the REST API.
  /// The agent's response will be received via the WebSocket stream.
  Future<void> sendChatMessage({
    required String sessionId,
    required String content,
  }) async {
    final url = '$_baseUrl/agents/chat/sessions/$sessionId/messages';
    final body = {'role': 'user', 'content': content};
    debugPrint(
      '⬆️ [ChatService] Sending chat message. URL: $url, Body: ${jsonEncode(body).length > 100 ? jsonEncode(body).substring(0, 100) + '...' : jsonEncode(body)}',
    );

    final response = await http.post(
      Uri.parse(url),
      headers: _headers,
      body: jsonEncode(body),
    );

    debugPrint(
      '⬇️ [ChatService] Send chat message response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Send chat message response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
      debugPrint('✅ [ChatService] User message sent successfully to REST API.');
    } else {
      debugPrint('❌ [ChatService] Failed to send message.');
      throw Exception(
        'Failed to send message: ${response.statusCode} - ${response.body}',
      );
    }
  }

  // ==================== FILE ATTACHMENTS ====================

  /// Upload a file attachment
  Future<Map<String, dynamic>> uploadFileAttachment({
    required File file,
    String? messageId,
  }) async {
    final url = '$_baseUrl/chat/attachments';
    debugPrint(
      '⬆️ [ChatService] Uploading file attachment. URL: $url, File: ${file.path}',
    );

    final request = http.MultipartRequest('POST', Uri.parse(url));

    request.headers.addAll({
      'Authorization': 'Bearer $_token',
    }); // Add token directly to multipart request headers

    request.files.add(await http.MultipartFile.fromPath('file', file.path));
    if (messageId != null) {
      request.fields['message_id'] = messageId;
    }

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    debugPrint(
      '⬇️ [ChatService] Upload file response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Upload file response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 201) {
      debugPrint('✅ [ChatService] File uploaded successfully.');
      return jsonDecode(response.body);
    } else {
      debugPrint('❌ [ChatService] Failed to upload file.');
      throw Exception(
        'Failed to upload file: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Get file attachment info
  Future<Map<String, dynamic>> getFileAttachment(String attachmentId) async {
    final url = '$_baseUrl/chat/attachments/$attachmentId';
    debugPrint('⬆️ [ChatService] Getting file attachment info. URL: $url');

    final response = await http.get(Uri.parse(url), headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Get file attachment info response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Get file attachment info response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] File attachment info fetched successfully.');
      return jsonDecode(response.body);
    } else {
      debugPrint('❌ [ChatService] Failed to get file attachment info.');
      throw Exception(
        'Failed to get file attachment: ${response.statusCode} - ${response.body}',
      );
    }
  }

  // ==================== CHAT SUMMARIES ====================

  /// Get chat summary for a session
  Future<ChatSummary?> getChatSummary(String sessionId) async {
    final url = '$_baseUrl/chat/sessions/$sessionId/summary';
    debugPrint('⬆️ [ChatService] Getting chat summary. URL: $url');

    final response = await http.get(Uri.parse(url), headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Get chat summary response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Get chat summary response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] Chat summary fetched successfully.');
      return ChatSummary.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 404) {
      debugPrint('⚠️ [ChatService] Chat summary not found (404).');
      return null; // No summary exists yet
    } else {
      debugPrint('❌ [ChatService] Failed to get chat summary.');
      throw Exception(
        'Failed to get chat summary: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Generate or update chat summary
  Future<ChatSummary> generateChatSummary(String sessionId) async {
    final url = '$_baseUrl/chat/sessions/$sessionId/summary';
    debugPrint('⬆️ [ChatService] Generating chat summary. URL: $url');

    final response = await http.post(Uri.parse(url), headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Generate chat summary response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Generate chat summary response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 201) {
      debugPrint('✅ [ChatService] Chat summary generated successfully.');
      return ChatSummary.fromJson(jsonDecode(response.body));
    } else {
      debugPrint('❌ [ChatService] Failed to generate chat summary.');
      throw Exception(
        'Failed to generate chat summary: ${response.statusCode} - ${response.body}',
      );
    }
  }

  // ==================== AGENTS (UPDATED) ====================

  /// Get agent with detailed chat statistics
  Future<AgentConfig> getAgentWithStats(String agentId) async {
    final url = '$_baseUrl/agents/$agentId';
    debugPrint('⬆️ [ChatService] Getting agent with stats. URL: $url');

    final response = await http.get(Uri.parse(url), headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Get agent with stats response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Get agent with stats response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] Agent with stats fetched successfully.');
      return AgentConfig.fromJson(jsonDecode(response.body));
    } else {
      debugPrint('❌ [ChatService] Failed to get agent with stats.');
      throw Exception(
        'Failed to get agent stats: ${response.statusCode} - ${response.body}',
      );
    }
  }

  // ==================== CHAT ANALYTICS ====================

  /// Get chat analytics for the current user
  Future<Map<String, dynamic>> getChatAnalytics({
    DateTime? startDate,
    DateTime? endDate,
    String? agentId,
  }) async {
    final queryParams = <String, String>{};
    if (startDate != null) {
      queryParams['start_date'] = startDate.toIso8601String();
    }
    if (endDate != null) {
      queryParams['end_date'] = endDate.toIso8601String();
    }
    if (agentId != null) queryParams['agent_id'] = agentId;

    final uri = Uri.parse(
      '$_baseUrl/chat/analytics',
    ).replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);
    debugPrint('⬆️ [ChatService] Getting chat analytics. URL: $uri');

    final response = await http.get(uri, headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Get chat analytics response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Get chat analytics response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] Chat analytics fetched successfully.');
      return jsonDecode(response.body);
    } else {
      debugPrint('❌ [ChatService] Failed to get chat analytics.');
      throw Exception(
        'Failed to get chat analytics: ${response.statusCode} - ${response.body}',
      );
    }
  }

  // ==================== SEARCH ====================

  /// Search chat history across sessions
  Future<List<Map<String, dynamic>>> searchChatHistory({
    required String query,
    String? agentId,
    DateTime? startDate,
    DateTime? endDate,
    int limit = 50,
  }) async {
    final queryParams = <String, String>{'q': query, 'limit': limit.toString()};
    if (agentId != null) queryParams['agent_id'] = agentId;
    if (startDate != null) {
      queryParams['start_date'] = startDate.toIso8601String();
    }
    if (endDate != null) {
      queryParams['end_date'] = endDate.toIso8601String();
    }

    final uri = Uri.parse(
      '$_baseUrl/chat/search',
    ).replace(queryParameters: queryParams);
    debugPrint('⬆️ [ChatService] Searching chat history. URL: $uri');

    final response = await http.get(uri, headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Search chat history response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Search chat history response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] Chat history search successful.');
      final List<dynamic> data = jsonDecode(response.body);
      return data.cast<Map<String, dynamic>>();
    } else {
      debugPrint('❌ [ChatService] Failed to search chat history.');
      throw Exception(
        'Failed to search chat history: ${response.statusCode} - ${response.body}',
      );
    }
  }

  // ==================== RAG / DOCUMENT PROCESSING ====================

  /// Process uploaded document for RAG
  Future<Map<String, dynamic>> processDocumentForRAG({
    required String attachmentId,
    String? agentId,
  }) async {
    final url = '$_baseUrl/rag/process';
    final body = {'attachment_id': attachmentId, 'agent_id': agentId};
    debugPrint(
      '⬆️ [ChatService] Processing document for RAG. URL: $url, Body: ${jsonEncode(body)}',
    );

    final response = await http.post(
      Uri.parse(url),
      headers: _headers,
      body: jsonEncode(body),
    );

    debugPrint(
      '⬇️ [ChatService] Process document for RAG response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Process document for RAG response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 202) {
      debugPrint('✅ [ChatService] Document processing initiated successfully.');
      return jsonDecode(response.body);
    } else {
      debugPrint('❌ [ChatService] Failed to process document for RAG.');
      throw Exception(
        'Failed to process document: ${response.statusCode} - ${response.body}',
      );
    }
  }

  /// Get RAG processing status
  Future<Map<String, dynamic>> getRagProcessingStatus(String jobId) async {
    final url = '$_baseUrl/rag/status/$jobId';
    debugPrint('⬆️ [ChatService] Getting RAG processing status. URL: $url');

    final response = await http.get(Uri.parse(url), headers: _headers);

    debugPrint(
      '⬇️ [ChatService] Get RAG processing status response status: ${response.statusCode}',
    );
    debugPrint(
      '⬇️ [ChatService] Get RAG processing status response body: ${response.body.length > 100 ? response.body.substring(0, 100) + '...' : response.body}',
    );

    if (response.statusCode == 200) {
      debugPrint('✅ [ChatService] RAG processing status fetched successfully.');
      return jsonDecode(response.body);
    } else {
      debugPrint('❌ [ChatService] Failed to get RAG processing status.');
      throw Exception(
        'Failed to get RAG status: ${response.statusCode} - ${response.body}',
      );
    }
  }
}
