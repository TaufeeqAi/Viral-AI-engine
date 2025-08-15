import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';

class EnhancedChatInput extends StatefulWidget {
  final Function(String, {List<String>? attachments}) onSendMessage;
  final bool enabled; // Overall enabled state (e.g., if AI is processing)
  final VoidCallback? onVoicePressed;
  final VoidCallback? onAttachPressed;
  final bool isStreaming; // Indicates if AI is currently streaming a response
  final VoidCallback? onStopStreaming; // Callback to stop streaming

  const EnhancedChatInput({
    super.key,
    required this.onSendMessage,
    this.enabled = true,
    this.onVoicePressed,
    this.onAttachPressed,
    this.isStreaming = false,
    this.onStopStreaming,
  });

  @override
  State<EnhancedChatInput> createState() => _EnhancedChatInputState();
}

class _EnhancedChatInputState extends State<EnhancedChatInput> {
  final TextEditingController _textController = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  List<PlatformFile> _attachedFiles = [];
  bool _isRecording = false;
  bool _hasText = false; // NEW: Tracks if there is any text in the input

  @override
  void initState() {
    super.initState();
    _textController.addListener(_updateHasText);
  }

  @override
  void dispose() {
    _textController.removeListener(_updateHasText); // Clean up listener
    _textController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _updateHasText() {
    setState(() {
      _hasText = _textController.text.trim().isNotEmpty;
    });
  }

  void _sendMessage() {
    final text = _textController.text.trim();
    if (text.isEmpty && _attachedFiles.isEmpty)
      return; // Should be prevented by button state

    final attachmentPaths = _attachedFiles
        .map((file) => file.path ?? '')
        .where((path) => path.isNotEmpty)
        .toList();

    widget.onSendMessage(
      text,
      attachments: attachmentPaths.isNotEmpty ? attachmentPaths : null,
    );

    _textController.clear();
    setState(() {
      _attachedFiles.clear();
      _hasText = false; // Reset _hasText after sending
    });
    _focusNode.unfocus(); // Unfocus the input after sending
  }

  Future<void> _handleAttachment() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: [
          'pdf',
          'txt',
          'doc',
          'docx',
          'json',
        ], // Added json for flexibility
        allowMultiple: true,
        withData: false, // No need for data if just sending path/name
      );

      if (result != null) {
        setState(() {
          _attachedFiles.addAll(result.files);
          _hasText = true; // Enable send button if files are attached
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error picking files: $e')));
    }
  }

  void _removeAttachment(int index) {
    setState(() {
      _attachedFiles.removeAt(index);
      if (_attachedFiles.isEmpty && _textController.text.trim().isEmpty) {
        _hasText = false; // Disable send button if no text and no files
      }
    });
  }

  void _handleVoiceInput() {
    setState(() {
      _isRecording = !_isRecording;
    });

    if (_isRecording) {
      // Start recording
      widget.onVoicePressed?.call();
    } else {
      // Stop recording
      widget.onVoicePressed?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    // Determine if the send/stop button should be enabled
    // It's enabled if:
    // 1. We are streaming (to allow stopping) AND onStopStreaming is provided.
    // 2. We are NOT streaming AND (has text OR has attachments).
    final bool isSendButtonEnabled =
        widget.enabled &&
        (widget.isStreaming
            ? (widget.onStopStreaming != null)
            : (_hasText || _attachedFiles.isNotEmpty));

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Attached files preview
          if (_attachedFiles.isNotEmpty) _buildAttachmentsPreview(),

          // Input row
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              // Attachment button
              IconButton(
                onPressed: widget.enabled && !widget.isStreaming
                    ? _handleAttachment
                    : null,
                icon: Icon(
                  Icons.attach_file,
                  color: widget.enabled && !widget.isStreaming
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(
                          context,
                        ).colorScheme.onSurface.withOpacity(0.38),
                ),
                tooltip: 'Attach files',
              ),

              // Text input
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: Theme.of(
                        context,
                      ).colorScheme.outline.withOpacity(0.3),
                    ),
                  ),
                  child: TextField(
                    controller: _textController,
                    focusNode: _focusNode,
                    enabled:
                        widget.enabled &&
                        !widget.isStreaming, // Disable if AI is streaming
                    maxLines: null, // Allows multiline input
                    textCapitalization: TextCapitalization.sentences,
                    decoration: InputDecoration(
                      hintText: widget.isStreaming
                          ? 'AI is typing...'
                          : 'Type your message...',
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                    ),
                    onSubmitted: isSendButtonEnabled && !widget.isStreaming
                        ? (_) => _sendMessage()
                        : null, // Only submit if enabled and not streaming
                  ),
                ),
              ),

              // Voice button
              IconButton(
                onPressed: widget.enabled && !widget.isStreaming
                    ? _handleVoiceInput
                    : null,
                icon: Icon(
                  _isRecording ? Icons.stop : Icons.mic,
                  color: _isRecording
                      ? Colors.red
                      : widget.enabled && !widget.isStreaming
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(
                          context,
                        ).colorScheme.onSurface.withOpacity(0.38),
                ),
                tooltip: _isRecording ? 'Stop recording' : 'Voice input',
              ),

              // Send/Stop button
              IconButton(
                onPressed: isSendButtonEnabled
                    ? (widget.isStreaming
                          ? widget.onStopStreaming
                          : _sendMessage)
                    : null, // Conditional action based on streaming state
                icon: Icon(
                  widget.isStreaming
                      ? Icons.stop
                      : Icons.send, // Conditional icon
                  color: isSendButtonEnabled
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(
                          context,
                        ).colorScheme.onSurface.withOpacity(0.38),
                ),
                tooltip: widget.isStreaming
                    ? 'Stop generation'
                    : 'Send message', // Conditional tooltip
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAttachmentsPreview() {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: _attachedFiles.asMap().entries.map((entry) {
          final index = entry.key;
          final file = entry.value;

          return Chip(
            avatar: Icon(_getFileIcon(file.extension ?? ''), size: 16),
            label: Text(file.name, style: const TextStyle(fontSize: 12)),
            deleteIcon: const Icon(Icons.close, size: 16),
            onDeleted: widget.enabled && !widget.isStreaming
                ? () => _removeAttachment(index)
                : null, // Disable deletion if streaming
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          );
        }).toList(),
      ),
    );
  }

  IconData _getFileIcon(String extension) {
    switch (extension.toLowerCase()) {
      case 'pdf':
        return Icons.picture_as_pdf;
      case 'txt':
        return Icons.text_snippet;
      case 'doc':
      case 'docx':
        return Icons.description;
      case 'json': // Added icon for JSON files
        return Icons.data_object;
      default:
        return Icons.attach_file;
    }
  }
}
