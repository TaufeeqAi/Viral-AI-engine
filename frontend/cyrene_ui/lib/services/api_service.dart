// services/api_service.dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter/foundation.dart'; // For debugPrint

import '../config/app_config.dart';
import '../models/agent_config.dart';
import '../models/chat_message.dart'; // Ensure ChatMessage is updated
import '../models/tool_model.dart'; // Assuming Tool and AgentTool are defined here

class ApiService {
  final String token;

  ApiService(this.token);

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer $token',
  };

  Future<List<AgentConfig>> getAgents() async {
    try {
      debugPrint('🔍 [ApiService] Fetching agents...');
      debugPrint('➡️ Request headers: $_headers');
      debugPrint('➡️ URL: ${AppConfig.fastApiBotUrl}/agents/list');
      final response = await http.get(
        Uri.parse('${AppConfig.fastApiBotUrl}/agents/list'),
        headers: _headers,
      );
      debugPrint('⬅️ Response status: ${response.statusCode}');
      debugPrint(
        '⬅️ Response body: ${response.body.length > 50 ? response.body.substring(0, 50) + '...' : response.body}',
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((json) => AgentConfig.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load agents: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<AgentConfig> createAgent(Map<String, dynamic> agentData) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.fastApiBotUrl}/agents/create'),
        headers: _headers,
        body: jsonEncode(agentData),
      );

      if (response.statusCode == 201) {
        return AgentConfig.fromJson(jsonDecode(response.body));
      } else {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? 'Failed to create agent');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<AgentConfig> updateAgent(
    String agentId,
    Map<String, dynamic> agentData,
  ) async {
    try {
      final response = await http.put(
        Uri.parse('${AppConfig.fastApiBotUrl}/agents/$agentId'),
        headers: _headers,
        body: jsonEncode(agentData),
      );

      if (response.statusCode == 200) {
        return AgentConfig.fromJson(jsonDecode(response.body));
      } else {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? 'Failed to update agent');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<void> deleteAgent(String agentId) async {
    try {
      final response = await http.delete(
        Uri.parse('${AppConfig.fastApiBotUrl}/agents/$agentId'),
        headers: _headers,
      );

      if (response.statusCode != 204) {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? 'Failed to delete agent');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // This method is likely deprecated if you're using ChatService for streaming
  Future<String> chatWithAgent(String agentId, String message) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.fastApiBotUrl}/agents/$agentId/chat'),
        headers: _headers,
        body: jsonEncode({'message': message}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['response'] ?? 'No response received';
      } else {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? 'Chat failed');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<List<ChatMessage>> getChatHistory(String agentId) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.fastApiBotUrl}/agents/$agentId/history'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((json) {
          // Determine MessageType based on 'type' or 'role' from backend
          // Assuming backend 'type' or 'role' directly maps to 'user' or 'assistant'/'agent'
          final String roleString =
              json['role'] as String? ??
              'system'; // Use 'role' if available, fallback to 'type'
          MessageType messageType;
          switch (roleString) {
            case 'user':
              messageType = MessageType.user;
              break;
            case 'assistant': // Backend might use 'assistant' for agent responses
              messageType = MessageType.agent;
              break;
            case 'system':
              messageType = MessageType.system;
              break;
            default:
              messageType = MessageType.system;
          }

          return ChatMessage(
            id: json['id'] as String,
            sessionId:
                json['session_id'] as String? ??
                '', // Provide session_id, assuming it's available
            role: roleString, // Pass the role string from backend
            content: json['content'] as String,
            type: messageType, // Use the derived MessageType
            timestamp: DateTime.parse(json['timestamp'] as String),
            isPartial:
                json['is_partial'] as bool? ?? false, // Ensure this is parsed
          );
        }).toList();
      } else {
        return [];
      }
    } catch (e) {
      debugPrint(
        'Error fetching chat history in ApiService: $e',
      ); // Changed to debugPrint
      return [];
    }
  }

  Future<AgentConfig> getAgentById(String agentId) async {
    try {
      debugPrint(
        '🔍 [ApiService] Fetching a single agent by ID: $agentId...',
      ); // Changed to debugPrint
      debugPrint('➡️ Request headers: $_headers'); // Changed to debugPrint
      debugPrint(
        '➡️ URL: ${AppConfig.fastApiBotUrl}/agents/$agentId',
      ); // Changed to debugPrint
      final response = await http.get(
        Uri.parse('${AppConfig.fastApiBotUrl}/agents/$agentId'),
        headers: _headers,
      );
      debugPrint(
        '⬅️ Response status: ${response.statusCode}',
      ); // Changed to debugPrint
      debugPrint('⬅️ Response body: ${response.body}'); // Changed to debugPrint

      if (response.statusCode == 200) {
        final currentAgent = jsonDecode(response.body); // FIX: Renamed variable
        debugPrint(
          'Agent Name: ${currentAgent['name']} pulled by its Id',
        ); // Changed to debugPrint
        return AgentConfig.fromJson(currentAgent);
      } else {
        throw Exception('Failed to load agents: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // --------- TOOL CRUD ---------
  Future<List<Tool>> getAllTools() async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.fastApiBotUrl}/tools'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((json) => Tool.fromJson(json)).toList();
      } else {
        throw Exception('Failed to fetch tools: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<Tool> getToolById(String toolId) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.fastApiBotUrl}/tools/$toolId'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        return Tool.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Tool not found: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<Tool> createOrUpdateTool(Map<String, dynamic> toolData) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.fastApiBotUrl}/tools'),
        headers: _headers,
        body: jsonEncode(toolData),
      );

      if (response.statusCode == 201) {
        return Tool.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to save tool: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<void> deleteTool(String toolId) async {
    try {
      final response = await http.delete(
        Uri.parse('${AppConfig.fastApiBotUrl}/tools/$toolId'),
        headers: _headers,
      );

      if (response.statusCode != 204) {
        throw Exception('Failed to delete tool: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // --------- AGENT-TOOL RELATIONS ---------

  Future<void> addToolToAgent(
    String agentId,
    String toolId, {
    bool isEnabled = true,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.fastApiBotUrl}/tools/$agentId/add/$toolId'),
        headers: _headers,
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to add tool to agent: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<void> removeToolFromAgent(String agentId, String toolId) async {
    try {
      final response = await http.delete(
        Uri.parse('${AppConfig.fastApiBotUrl}/tools/$agentId/remove/$toolId'),
        headers: _headers,
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to remove tool: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<void> toggleToolStatus(
    String agentId,
    String toolId,
    bool isEnabled,
  ) async {
    try {
      final uri = Uri.parse(
        '${AppConfig.fastApiBotUrl}/tools/$agentId/toggle/$toolId?is_enabled=$isEnabled',
      );
      final response = await http.patch(uri, headers: _headers);

      if (response.statusCode != 200) {
        throw Exception('Failed to toggle tool: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  Future<List<AgentTool>> getAgentTools(String agentId) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConfig.fastApiBotUrl}/tools/$agentId/agent-tools'),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((json) => AgentTool.fromJson(json)).toList();
      } else {
        throw Exception('Failed to fetch agent tools: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
}
