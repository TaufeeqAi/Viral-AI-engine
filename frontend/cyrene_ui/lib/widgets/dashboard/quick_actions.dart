// lib/widgets/dashboard/quick_actions.dart

import 'package:flutter/material.dart';

class QuickActions extends StatelessWidget {
  final VoidCallback onCreateAgent;
  final VoidCallback onViewAgents;
  final VoidCallback onStartChat;

  const QuickActions({
    super.key,
    required this.onCreateAgent,
    required this.onViewAgents,
    required this.onStartChat,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quick Actions',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _buildActionButton(
                  context,
                  'Create Agent',
                  Icons.add_circle,
                  Colors.blue,
                  onCreateAgent,
                ),
                _buildActionButton(
                  context,
                  'View Agents',
                  Icons.list,
                  Colors.green,
                  onViewAgents,
                ),
                _buildActionButton(
                  context,
                  'Start Chat',
                  Icons.chat,
                  Colors.orange,
                  onStartChat,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton(
    BuildContext context,
    String label,
    IconData icon,
    Color color,
    VoidCallback onPressed,
  ) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color.withOpacity(0.1),
        foregroundColor: color,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    );
  }
}
