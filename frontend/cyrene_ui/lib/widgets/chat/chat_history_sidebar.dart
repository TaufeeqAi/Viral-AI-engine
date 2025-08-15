import 'package:flutter/material.dart';
import '../../models/chat_session.dart';

class ChatHistorySidebar extends StatefulWidget {
  final List<ChatSession> chatSessions;
  final String? currentSessionId;
  final Function(ChatSession) onSessionSelected;
  final VoidCallback onNewChat;
  final VoidCallback onClose;

  const ChatHistorySidebar({
    super.key,
    required this.chatSessions,
    this.currentSessionId,
    required this.onSessionSelected,
    required this.onNewChat,
    required this.onClose,
  });

  @override
  State<ChatHistorySidebar> createState() => _ChatHistorySidebarState();
}

class _ChatHistorySidebarState extends State<ChatHistorySidebar> {
  String _searchQuery = '';
  String _selectedTimeFilter = 'all'; // all, today, week, month
  final TextEditingController _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<ChatSession> get _filteredSessions {
    var sessions = widget.chatSessions;

    // Apply search filter
    if (_searchQuery.isNotEmpty) {
      sessions = sessions.where((session) {
        return session.title.toLowerCase().contains(_searchQuery.toLowerCase());
      }).toList();
    }

    // Apply time filter
    final now = DateTime.now();
    switch (_selectedTimeFilter) {
      case 'today':
        sessions = sessions.where((session) {
          return session.updatedAt.day == now.day &&
              session.updatedAt.month == now.month &&
              session.updatedAt.year == now.year;
        }).toList();
        break;
      case 'week':
        final weekAgo = now.subtract(const Duration(days: 7));
        sessions = sessions.where((session) {
          return session.updatedAt.isAfter(weekAgo);
        }).toList();
        break;
      case 'month':
        final monthAgo = now.subtract(const Duration(days: 30));
        sessions = sessions.where((session) {
          return session.updatedAt.isAfter(monthAgo);
        }).toList();
        break;
    }

    // Sort by most recent
    sessions.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return sessions;
  }

  Map<String, List<ChatSession>> get _groupedSessions {
    final filtered = _filteredSessions;
    final grouped = <String, List<ChatSession>>{};
    final now = DateTime.now();

    for (final session in filtered) {
      String groupKey;
      final difference = now.difference(session.updatedAt).inDays;

      if (difference == 0) {
        groupKey = 'Today';
      } else if (difference == 1) {
        groupKey = 'Yesterday';
      } else if (difference <= 7) {
        groupKey = 'This Week';
      } else if (difference <= 30) {
        groupKey = 'This Month';
      } else {
        groupKey = 'Older';
      }

      grouped.putIfAbsent(groupKey, () => []);
      grouped[groupKey]!.add(session);
    }

    return grouped;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 320,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          right: BorderSide(
            color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2),
          ),
        ),
      ),
      child: Column(
        children: [
          _buildHeader(),
          _buildSearchAndFilter(),
          Expanded(child: _buildChatList()),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2),
          ),
        ),
      ),
      child: Row(
        children: [
          Text(
            'Chat History',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: widget.onNewChat,
            tooltip: 'New Chat',
            iconSize: 20,
          ),
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: widget.onClose,
            tooltip: 'Close',
            iconSize: 20,
          ),
        ],
      ),
    );
  }

  Widget _buildSearchAndFilter() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Search bar
          TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'Search chats...',
              prefixIcon: const Icon(Icons.search, size: 20),
              suffixIcon: _searchQuery.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear, size: 20),
                      onPressed: () {
                        _searchController.clear();
                        setState(() {
                          _searchQuery = '';
                        });
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(
                  color: Theme.of(
                    context,
                  ).colorScheme.outline.withValues(alpha: 0.3),
                ),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 8,
              ),
            ),
            onChanged: (value) {
              setState(() {
                _searchQuery = value;
              });
            },
          ),

          const SizedBox(height: 12),

          // Time filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildFilterChip('All', 'all'),
                const SizedBox(width: 8),
                _buildFilterChip('Today', 'today'),
                const SizedBox(width: 8),
                _buildFilterChip('Week', 'week'),
                const SizedBox(width: 8),
                _buildFilterChip('Month', 'month'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, String value) {
    final isSelected = _selectedTimeFilter == value;
    return FilterChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        setState(() {
          _selectedTimeFilter = selected ? value : 'all';
        });
      },
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  Widget _buildChatList() {
    final groupedSessions = _groupedSessions;

    if (groupedSessions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.chat_bubble_outline,
              size: 48,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              _searchQuery.isNotEmpty ? 'No chats found' : 'No chat history',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            if (_searchQuery.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                'Try adjusting your search',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      itemCount: groupedSessions.entries.length,
      itemBuilder: (context, index) {
        final entry = groupedSessions.entries.elementAt(index);
        final groupName = entry.key;
        final sessions = entry.value;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Group header
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Text(
                groupName,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),

            // Sessions in this group
            ...sessions.map((session) => _buildChatSessionTile(session)),

            const SizedBox(height: 8),
          ],
        );
      },
    );
  }

  Widget _buildChatSessionTile(ChatSession session) {
    final isSelected = session.id == widget.currentSessionId;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      child: Material(
        color: isSelected
            ? Theme.of(
                context,
              ).colorScheme.primaryContainer.withValues(alpha: 0.5)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: () => widget.onSessionSelected(session),
          child: Container(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                // Chat icon
                Icon(
                  Icons.chat_bubble_outline,
                  size: 16,
                  color: isSelected
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).colorScheme.onSurfaceVariant,
                ),

                const SizedBox(width: 12),

                // Chat details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        session.title,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontWeight: isSelected
                              ? FontWeight.w600
                              : FontWeight.normal,
                          color: isSelected
                              ? Theme.of(context).colorScheme.primary
                              : null,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),

                      const SizedBox(height: 4),

                      Text(
                        _formatRelativeTime(session.updatedAt),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),

                // More options
                IconButton(
                  icon: const Icon(Icons.more_vert, size: 16),
                  onPressed: () => _showSessionOptions(session),
                  tooltip: 'More options',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showSessionOptions(ChatSession session) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.edit),
            title: const Text('Rename'),
            onTap: () {
              Navigator.pop(context);
              _showRenameDialog(session);
            },
          ),
          ListTile(
            leading: const Icon(Icons.share),
            title: const Text('Share'),
            onTap: () {
              Navigator.pop(context);
              // TODO: Implement share functionality
            },
          ),
          ListTile(
            leading: const Icon(Icons.delete, color: Colors.red),
            title: const Text('Delete', style: TextStyle(color: Colors.red)),
            onTap: () {
              Navigator.pop(context);
              _showDeleteDialog(session);
            },
          ),
        ],
      ),
    );
  }

  void _showRenameDialog(ChatSession session) {
    final controller = TextEditingController(text: session.title);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename Chat'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Chat title',
            border: OutlineInputBorder(),
          ),
          maxLines: 2,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              // TODO: Implement rename functionality
              Navigator.pop(context);
            },
            child: const Text('Rename'),
          ),
        ],
      ),
    );
  }

  void _showDeleteDialog(ChatSession session) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Chat'),
        content: Text('Are you sure you want to delete "${session.title}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              // TODO: Implement delete functionality
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  String _formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
    }
  }
}
