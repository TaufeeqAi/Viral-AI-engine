import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../models/chat_message.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;
  final bool showAvatar;
  final bool isLastMessage;

  const MessageBubble({
    super.key,
    required this.message,
    this.showAvatar = true,
    this.isLastMessage = false,
  });

  @override
  Widget build(BuildContext context) {
    final isUser = message.type == MessageType.user;
    final isError = message.type == MessageType.error;

    return Container(
      margin: EdgeInsets.only(
        bottom: isLastMessage ? 16 : 8,
        left: isUser ? 64 : 0,
        right: isUser ? 0 : 64,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: isUser
            ? MainAxisAlignment.end
            : MainAxisAlignment.start,
        children: [
          if (!isUser && showAvatar) _buildAvatar(context),
          if (!isUser && !showAvatar) const SizedBox(width: 40),
          Flexible(child: _buildMessageContent(context, isUser, isError)),
          if (isUser && showAvatar) _buildUserAvatar(context),
          if (isUser && !showAvatar) const SizedBox(width: 40),
        ],
      ),
    );
  }

  Widget _buildAvatar(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(right: 8, bottom: 4),
      child: CircleAvatar(
        radius: 16,
        backgroundColor: Theme.of(context).colorScheme.primary,
        child: const Icon(Icons.psychology, color: Colors.white, size: 16),
      ),
    );
  }

  Widget _buildUserAvatar(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(left: 8, bottom: 4),
      child: CircleAvatar(
        radius: 16,
        backgroundColor: Theme.of(context).colorScheme.secondary,
        child: const Icon(Icons.person, color: Colors.white, size: 16),
      ),
    );
  }

  Widget _buildMessageContent(BuildContext context, bool isUser, bool isError) {
    Color backgroundColor;
    Color textColor;

    if (isError) {
      backgroundColor = Theme.of(context).colorScheme.errorContainer;
      textColor = Theme.of(context).colorScheme.onErrorContainer;
    } else if (isUser) {
      backgroundColor = Theme.of(context).colorScheme.primary;
      textColor = Colors.white;
    } else {
      backgroundColor = Theme.of(context).colorScheme.surfaceVariant;
      textColor = Theme.of(context).colorScheme.onSurfaceVariant;
    }

    return GestureDetector(
      onLongPress: () => _showMessageOptions(context),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(16).copyWith(
            bottomLeft: !isUser && showAvatar ? const Radius.circular(4) : null,
            bottomRight: isUser && showAvatar ? const Radius.circular(4) : null,
          ),
          boxShadow: [
            BoxShadow(
              color: Theme.of(context).colorScheme.shadow.withOpacity(0.1),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (message.isLoading)
              _buildLoadingIndicator(textColor)
            else
              Text(
                message.textContent, // MODIFIED: Use message.textContent here
                style: TextStyle(color: textColor, fontSize: 15, height: 1.4),
              ),
            if (showAvatar) ...[
              const SizedBox(height: 4),
              Text(
                _formatTime(message.timestamp),
                style: TextStyle(
                  color: textColor.withOpacity(0.7),
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingIndicator(Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'Typing...',
          style: TextStyle(
            color: color.withOpacity(0.7),
            fontStyle: FontStyle.italic,
          ),
        ),
      ],
    );
  }

  void _showMessageOptions(BuildContext context) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.copy),
              title: const Text('Copy Message'),
              onTap: () {
                Clipboard.setData(
                  ClipboardData(text: message.textContent),
                ); // MODIFIED: Use message.textContent here
                Navigator.of(context).pop();
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Message copied to clipboard')),
                );
              },
            ),
            if (message.type == MessageType.agent) ...[
              ListTile(
                leading: const Icon(Icons.refresh),
                title: const Text('Regenerate Response'),
                onTap: () {
                  Navigator.of(context).pop();
                  // TODO: Implement regenerate
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inDays > 0) {
      return '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }
}
