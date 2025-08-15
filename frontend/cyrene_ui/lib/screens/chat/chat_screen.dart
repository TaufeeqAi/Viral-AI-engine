import 'package:cyrene_ui/models/agent_config.dart';
import 'package:cyrene_ui/models/chat_message.dart';
import 'package:cyrene_ui/services/api_service.dart';
import 'package:cyrene_ui/services/auth_service.dart';
import 'package:cyrene_ui/services/chat_service.dart';
import 'package:cyrene_ui/widgets/chat/chat_input.dart';
import 'package:cyrene_ui/widgets/chat/message_bubble.dart';
import 'package:cyrene_ui/widgets/chat/streaming_message_bubble.dart';
import 'package:cyrene_ui/widgets/common/empty_state.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ChatScreen extends StatefulWidget {
  // agentId and agentName from widget are no longer directly used for initial selection
  // but can still be passed if needed for other purposes (e.g., deep linking to a specific agent's chat)
  final String? agentId;
  final String? agentName;
  final String? sessionId;
  final bool? showAllHistory;

  const ChatScreen({
    super.key,
    this.agentId,
    this.agentName,
    this.sessionId,
    this.showAllHistory,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _isStreamingResponse = false;
  bool _isLoadingHistory = false; // State for history loading

  List<AgentConfig> _availableAgents = [];
  String? _currentAgentId;
  String? _currentAgentName;
  String? _currentSessionId;
  String? _currentUserId;

  late ChatService _chatService;
  StreamSubscription<ChatMessage>? _messageSubscription;

  static const String _lastSelectedAgentKey = 'lastSelectedAgentId';

  @override
  void initState() {
    super.initState();
    _chatService = Provider.of<ChatService>(context, listen: false);
    _currentUserId = Provider.of<AuthService>(context, listen: false).userId;

    // Always load and set the initial agent based on persistence or default
    _loadAndSetInitialAgent();
  }

  Future<void> _loadAndSetInitialAgent() async {
    debugPrint('[_loadAndSetInitialAgent] Starting agent load and set...');
    await _loadAvailableAgents(); // Load all agents first

    if (!mounted) {
      debugPrint('[_loadAndSetInitialAgent] Widget not mounted, returning.');
      return;
    }

    // Always try to load from SharedPreferences first, or default to first available
    final prefs = await SharedPreferences.getInstance();
    final lastSelectedAgentId = prefs.getString(_lastSelectedAgentKey);
    debugPrint(
      '[_loadAndSetInitialAgent] Last selected agent from prefs: $lastSelectedAgentId',
    );

    if (lastSelectedAgentId != null &&
        _availableAgents.any((agent) => agent.id == lastSelectedAgentId)) {
      // If a previously selected agent exists and is still available
      _currentAgentId = lastSelectedAgentId;
      _currentAgentName = _availableAgents
          .firstWhere((agent) => agent.id == lastSelectedAgentId)
          .name;
      debugPrint(
        '[_loadAndSetInitialAgent] Using last selected agent: $_currentAgentName (ID: $_currentAgentId)',
      );
    } else if (_availableAgents.isNotEmpty) {
      // If no saved agent or it's unavailable, default to the first available agent
      _currentAgentId = _availableAgents.first.id;
      _currentAgentName = _availableAgents.first.name;
      _saveLastSelectedAgent(_currentAgentId!); // Save this as the new default
      debugPrint(
        '[_loadAndSetInitialAgent] Defaulting to first available agent: $_currentAgentName (ID: $_currentAgentId)',
      );
    } else {
      // No agents available at all
      _currentAgentId = null;
      _currentAgentName = null;
      debugPrint('[_loadAndSetInitialAgent] No agents available to select.');
    }

    // If a sessionId was passed in the widget, prioritize loading that specific session
    // This allows for deep linking or navigation to a specific chat history
    if (widget.sessionId != null) {
      _currentSessionId = widget.sessionId;
      debugPrint(
        '[_loadAndSetInitialAgent] Widget sessionId provided: $_currentSessionId. Prioritizing history load.',
      );
    } else {
      _currentSessionId =
          null; // Ensure no old session is carried over if not explicitly provided
    }

    // Now that _currentAgentId is set (or remains null if no agents), proceed
    if (_currentAgentId != null) {
      debugPrint(
        '[_loadAndSetInitialAgent] Current Agent ID set: $_currentAgentId. Loading history and initializing WebSocket.',
      );
      if (_currentSessionId != null) {
        await _loadChatHistory();
      }
      await _initializeWebSocket();
    } else {
      debugPrint(
        '[_loadAndSetInitialAgent] No agents available or selected. Displaying empty state.',
      );
      setState(() {}); // Trigger rebuild to show empty state
    }
  }

  Future<void> _saveLastSelectedAgent(String agentId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lastSelectedAgentKey, agentId);
    debugPrint('[SharedPreferences] Saved last selected agent: $agentId');
  }

  @override
  void didUpdateWidget(ChatScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    debugPrint(
      '[didUpdateWidget] Widget updated. Old Agent: ${oldWidget.agentId}, New Agent: ${widget.agentId}',
    );
    debugPrint(
      '[didUpdateWidget] Old Session: ${oldWidget.sessionId}, New Session: ${widget.sessionId}',
    );

    // Only update session if it explicitly changed from the widget.
    // Agent selection is now managed internally by _loadAndSetInitialAgent and _switchAgent.
    if (widget.sessionId != oldWidget.sessionId) {
      _messages.clear(); // Clear messages if session changes
      _currentSessionId = widget.sessionId; // Update current session ID
      debugPrint(
        '[didUpdateWidget] Session ID changed. Clearing messages and re-initializing WebSocket.',
      );

      if (_currentSessionId != null) {
        _loadChatHistory(); // Load history for the new session
      }
      _initializeWebSocket(); // Re-initialize WebSocket for the new session
    }
    // No need to handle agentId changes from widget here, as internal state manages it.
  }

  @override
  void dispose() {
    debugPrint('[dispose] Disposing ChatScreen resources.');
    _scrollController.dispose();
    _messageSubscription?.cancel();
    _chatService.disconnectChatWebSocket();
    super.dispose();
  }

  Future<void> _loadAvailableAgents() async {
    debugPrint('[_loadAvailableAgents] Fetching available agents...');
    try {
      if (!mounted) return;
      final authService = Provider.of<AuthService>(context, listen: false);
      final apiService = ApiService(authService.token!);

      final agents = await apiService.getAgents();
      if (!mounted) return;
      setState(() {
        _availableAgents = agents;
      });
      debugPrint(
        '[_loadAvailableAgents] Loaded ${agents.length} available agents.',
      );
    } catch (e) {
      debugPrint('[_loadAvailableAgents] Error loading agents: $e');
    }
  }

  Future<void> _initializeWebSocket() async {
    debugPrint('[_initializeWebSocket] Initializing WebSocket...');
    _messageSubscription?.cancel(); // Cancel any existing subscription

    if (_currentSessionId != null) {
      try {
        debugPrint(
          '[_initializeWebSocket] Attempting to connect WebSocket for session: $_currentSessionId',
        );
        await _chatService.connectChatWebSocket(_currentSessionId!);
        _messageSubscription = _chatService.messages.listen(
          (message) {
            debugPrint(
              '[_initializeWebSocket] WebSocket Stream Received event: ${message.id}, Role: ${message.role}, Partial: ${message.isPartial}, Content: ${message.textContent.length > 50 ? message.textContent.substring(0, 50) + '...' : message.textContent}',
            );

            if (!mounted) {
              debugPrint(
                '[_initializeWebSocket] Widget not mounted during stream, skipping update.',
              );
              return;
            }

            setState(() {
              final existingMessageIndex = _messages.indexWhere(
                (msg) => msg.id == message.id,
              );

              if (message.role == 'user') {
                // This is an echo of the user's message from the backend
                if (existingMessageIndex == -1) {
                  // Only add if it's not already in our local list (prevents duplicates)
                  _messages.add(
                    message.copyWith(isLoading: false, isPartial: false),
                  );
                  debugPrint(
                    '[_initializeWebSocket] Added new user message echo: ${message.id}',
                  );
                } else {
                  debugPrint(
                    '[_initializeWebSocket] User message echo already exists, skipping: ${message.id}',
                  );
                  // Optionally, update the existing user message if there's any difference
                  // _messages[existingMessageIndex] = message.copyWith(isLoading: false, isPartial: false);
                }
              } else if (message.role == 'agent') {
                if (message.isPartial) {
                  // This is an LLM streaming chunk
                  _isStreamingResponse = true;
                  if (existingMessageIndex != -1) {
                    // Update existing partial message (append content)
                    _messages[existingMessageIndex] =
                        _messages[existingMessageIndex].copyWith(
                          content: {
                            'text':
                                _messages[existingMessageIndex].textContent +
                                message.textContent,
                          },
                          isLoading: true, // Keep loading state for partials
                          isPartial: true, // Ensure it remains partial
                        );
                    debugPrint(
                      '[_initializeWebSocket] Updated existing partial agent message: ${message.id}',
                    );
                  } else {
                    // Add a new partial message (first chunk for a new AI response)
                    _messages.add(
                      ChatMessage(
                        id: message.id,
                        sessionId: message.sessionId,
                        role: message.role,
                        content: message.content,
                        type: message.type,
                        timestamp: message.timestamp,
                        isPartial: true,
                        isLoading: true,
                      ),
                    );
                    debugPrint(
                      '[_initializeWebSocket] Added new partial agent message: ${message.id}',
                    );
                  }
                } else {
                  // This is a complete agent message (final response)
                  if (existingMessageIndex != -1) {
                    // Update existing partial message to complete
                    _messages[existingMessageIndex] = message.copyWith(
                      isLoading: false,
                      isPartial: false,
                      content: message
                          .content, // Use the full content from the final message
                    );
                    debugPrint(
                      '[_initializeWebSocket] Updated existing agent message to complete: ${message.id}',
                    );
                  } else {
                    // Add as a new complete message (fallback, should ideally update an existing partial)
                    _messages.add(
                      message.copyWith(isLoading: false, isPartial: false),
                    );
                    debugPrint(
                      '[_initializeWebSocket] Added new complete agent message (fallback): ${message.id}',
                    );
                  }
                  _isStreamingResponse =
                      false; // Streaming is complete for this message
                }
              }
            });
            _scrollToBottom();
          },
          onError: (error) {
            debugPrint('[_initializeWebSocket] WebSocket Stream Error: $error');
            _handleStreamingError(error.toString());
          },
          onDone: () {
            debugPrint('[_initializeWebSocket] WebSocket Stream Done.');
            if (!mounted) return;
            setState(() {
              _isStreamingResponse = false;
              // Ensure any remaining partial agent message is marked as complete
              if (_messages.isNotEmpty &&
                  _messages.last.role == 'agent' &&
                  _messages.last.isPartial) {
                _messages.last = _messages.last.copyWith(
                  isLoading: false,
                  isPartial: false,
                );
                debugPrint(
                  '[_initializeWebSocket] Finalized last partial agent message on stream done.',
                );
              }
            });
          },
        );
      } catch (e) {
        debugPrint(
          '[_initializeWebSocket] Failed to connect WebSocket for session $_currentSessionId: $e',
        );
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to connect to real-time chat: $e')),
        );
      }
    } else {
      debugPrint(
        '[_initializeWebSocket] No session ID available to connect WebSocket. Will connect on first message.',
      );
    }
  }

  Future<void> _loadChatHistory() async {
    debugPrint(
      '[_loadChatHistory] Loading chat history for session: $_currentSessionId',
    );
    if (_currentSessionId == null) {
      debugPrint(
        '[_loadChatHistory] No current session ID, skipping history load.',
      );
      return;
    }

    setState(() {
      _isLoadingHistory = true; // Set loading state
    });

    try {
      final history = await _chatService.getChatSessionHistory(
        _currentSessionId!,
      );
      if (!mounted) {
        debugPrint('[_loadChatHistory] Widget not mounted, returning.');
        return;
      }
      setState(() {
        _messages.clear();
        _messages.addAll(history);
        _isLoadingHistory = false; // Clear loading state
      });
      debugPrint(
        '[_loadChatHistory] Loaded ${history.length} messages for session: $_currentSessionId',
      );

      _scrollToBottom();
      // After loading history, connect WebSocket to this session
      await _initializeWebSocket(); // Re-initialize WebSocket for the loaded session
    } catch (e) {
      debugPrint('[_loadChatHistory] Error loading chat history: $e');
      if (!mounted) return;
      setState(() {
        _isLoadingHistory = false; // Clear loading state on error
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load chat history: $e')),
      );
    }
  }

  Future<void> _switchAgent(String agentId, String agentName) async {
    debugPrint('[_switchAgent] Switching to agent: $agentName (ID: $agentId)');
    setState(() {
      _currentAgentId = agentId;
      _currentAgentName = agentName;
      _messages.clear();
      _currentSessionId = null; // Will create new session on first message
      _isStreamingResponse = false; // Reset streaming state
    });
    _saveLastSelectedAgent(agentId); // Save the newly selected agent
    _chatService
        .disconnectChatWebSocket(); // Disconnect old session's WebSocket
    debugPrint(
      '[_switchAgent] Switched agent. Messages cleared, new session will be created on next message.',
    );
    // _initializeWebSocket() will be called on the first message if _currentSessionId is null
  }

  Future<void> _sendMessage(String message, {List<String>? attachments}) async {
    debugPrint('[_sendMessage] User sending message: "$message"');
    if (message.trim().isEmpty ||
        _currentAgentId == null ||
        _currentUserId == null) {
      debugPrint(
        '[_sendMessage] Message empty, agent not selected, or user not logged in. Skipping send.',
      );
      return;
    }

    // Add user message to UI immediately
    final userMessage = ChatMessage.user(message);
    if (!mounted) return;
    setState(() {
      _messages.add(userMessage);
      // _isStreamingResponse = true; // ONLY set this when AI starts responding
    });
    _scrollToBottom();

    try {
      if (_currentSessionId == null) {
        debugPrint(
          '[_sendMessage] No current session. Creating new chat session...',
        );
        _currentSessionId = await _createNewChatSession(message);
        await _initializeWebSocket(); // Connect WebSocket to the new session
        debugPrint(
          '[_sendMessage] New session created and WebSocket initialized for: $_currentSessionId',
        );
      }

      debugPrint(
        '[_sendMessage] Sending chat message to REST API for session: $_currentSessionId',
      );
      await _chatService.sendChatMessage(
        sessionId: _currentSessionId!,
        content: userMessage.textContent,
      );
      debugPrint('[_sendMessage] User message sent to REST API successfully.');
      // The AI response will come via WebSocket, which will then set _isStreamingResponse = true
    } catch (e) {
      debugPrint('[_sendMessage] Error sending message: $e');
      _handleStreamingError(e.toString());
    }
  }

  Future<String> _createNewChatSession(String firstMessage) async {
    debugPrint(
      '[_createNewChatSession] Creating new chat session with first message: "$firstMessage"',
    );
    try {
      final title = firstMessage.length > 50
          ? '${firstMessage.substring(0, 50)}...'
          : firstMessage;

      final session = await _chatService.createChatSession(
        userId: _currentUserId!,
        agentId: _currentAgentId!,
        title: title,
      );
      debugPrint(
        '[_createNewChatSession] New chat session created: ${session.id}',
      );
      return session.id;
    } catch (e) {
      debugPrint('[_createNewChatSession] Failed to create chat session: $e');
      throw Exception('Failed to create chat session: $e');
    }
  }

  void _handleStreamingError(String error) {
    debugPrint('[_handleStreamingError] Handling streaming error: $error');
    final errorMessage = ChatMessage.error('Error: $error');
    if (!mounted) return;
    setState(() {
      _messages.add(errorMessage);
      _isStreamingResponse = false; // Ensure streaming is off
      // Ensure any partial message is finalized
      if (_messages.isNotEmpty && _messages.last.isPartial) {
        _messages.last = _messages.last.copyWith(
          isLoading: false,
          isPartial: false,
        );
      }
    });
    _scrollToBottom();
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('Chat error: $error')));
  }

  // TODO: Implement this method for stopping AI generation
  void _handleStopStreaming() {
    debugPrint(
      '[_handleStopStreaming] Stop button pressed. Sending stop signal...',
    );
    // You need to implement the backend API call to stop the streaming here.
    // For now, we'll just stop the frontend indicator.
    if (!mounted) return;
    setState(() {
      _isStreamingResponse = false;
      if (_messages.isNotEmpty &&
          _messages.last.role == 'agent' &&
          _messages.last.isPartial) {
        _messages.last = _messages.last.copyWith(
          isLoading: false,
          isPartial: false,
        );
      }
    });
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('AI response stopped.')));
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _clearChat() {
    debugPrint('[_clearChat] Clearing chat...');
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Chat'),
        content: const Text(
          'Are you sure you want to clear the current chat session?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.of(context).pop();
              if (_currentSessionId != null) {
                try {
                  debugPrint(
                    '[_clearChat] Deleting chat session $_currentSessionId from backend.',
                  );
                  await _chatService.deleteChatSession(_currentSessionId!);
                  debugPrint(
                    '[_clearChat] Chat session $_currentSessionId deleted from backend.',
                  );
                } catch (e) {
                  debugPrint(
                    '[_clearChat] Error deleting chat session from backend: $e',
                  );
                  if (!mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Failed to delete session: $e')),
                  );
                }
              }
              if (!mounted) return;
              setState(() {
                _messages.clear();
                _currentSessionId = null;
                _isStreamingResponse = false;
              });
              _chatService.disconnectChatWebSocket();
              debugPrint(
                '[_clearChat] Chat cleared and WebSocket disconnected.',
              );
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Clear'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_currentAgentId == null) {
      debugPrint('[build] No current agent selected. Showing empty state.');
      return EmptyState(
        icon: Icons.chat_bubble_outline,
        title: 'No Agent Selected',
        subtitle: _availableAgents.isEmpty
            ? 'No agents available. Please create one.'
            : 'Please select an agent to start chatting.',
        action: ElevatedButton.icon(
          onPressed: () {
            // TODO: Navigate to agents tab or creation screen
            debugPrint(
              '[build] Navigate to agents tab functionality not implemented.',
            );
          },
          icon: const Icon(Icons.smart_toy),
          label: const Text('View Agents'),
        ),
      );
    }

    return Column(
      children: [
        _buildChatHeader(),
        Expanded(child: _buildChatArea()),
        EnhancedChatInput(
          onSendMessage: _sendMessage,
          enabled:
              !_isStreamingResponse, // Still controls overall enabled state
          onVoicePressed: _handleVoiceInput,
          onAttachPressed: _handleAttachment,
          isStreaming:
              _isStreamingResponse, // Pass streaming state to control button icon
          onStopStreaming: _handleStopStreaming, // Pass the stop handler
        ),
      ],
    );
  }

  Widget _buildChatHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(
          context,
        ).colorScheme.surfaceContainerHighest.withAlpha((255 * 0.3).round()),
        border: Border(
          bottom: BorderSide(
            color: Theme.of(
              context,
            ).colorScheme.outline.withAlpha((255 * 0.2).round()),
          ),
        ),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor: Theme.of(context).colorScheme.primary,
            child: const Icon(Icons.psychology, color: Colors.white, size: 16),
          ),
          const SizedBox(width: 12),
          Expanded(child: _buildAgentDropdown()),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadChatHistory,
            tooltip: 'Refresh chat',
          ),
          IconButton(
            icon: const Icon(Icons.clear_all),
            onPressed: _clearChat,
            tooltip: 'Clear chat',
          ),
        ],
      ),
    );
  }

  Widget _buildAgentDropdown() {
    return DropdownButtonHideUnderline(
      child: DropdownButton<String>(
        value: _currentAgentId,
        isExpanded: true,
        items: _availableAgents.map((agent) {
          return DropdownMenuItem<String>(
            value: agent.id,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  agent.name,
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                ),
                Text(
                  'Online',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: Colors.green),
                ),
              ],
            ),
          );
        }).toList(),
        onChanged: (String? newAgentId) {
          if (newAgentId != null) {
            final selectedAgent = _availableAgents.firstWhere(
              (agent) => agent.id == newAgentId,
            );
            _switchAgent(newAgentId, selectedAgent.name);
          }
        },
      ),
    );
  }

  Widget _buildChatArea() {
    // Show loading indicator if history is being loaded
    if (_isLoadingHistory) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_messages.isEmpty && !_isStreamingResponse) {
      return EmptyState(
        icon: Icons.chat_bubble_outline,
        title: 'Start a Conversation',
        subtitle:
            'Send a message to ${_currentAgentName ?? 'your agent'} to begin chatting.',
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(16),
      itemCount: _messages.length,
      itemBuilder: (context, index) {
        final message = _messages[index];
        final isLastMessage = index == _messages.length - 1;

        final showAvatar =
            index == 0 || _messages[index - 1].type != message.type;

        // Use StreamingMessageBubble only for the last partial agent message when streaming is active
        if (isLastMessage && message.isPartial && _isStreamingResponse) {
          return StreamingMessageBubble(content: message.textContent);
        } else {
          return MessageBubble(
            message: message,
            showAvatar: showAvatar,
            isLastMessage: isLastMessage,
          );
        }
      },
    );
  }

  void _handleVoiceInput() {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Voice input coming soon!')));
  }

  void _handleAttachment() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('File attachment coming soon!')),
    );
  }
}
