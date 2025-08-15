// lib/widgets/common/custom_drawer.dart

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/auth_service.dart';
import '../../config/app_config.dart';

class CustomDrawer extends StatelessWidget {
  final int selectedIndex;
  final Function(int) onItemSelected;
  final String? selectedAgentName;

  const CustomDrawer({
    super.key,
    required this.selectedIndex,
    required this.onItemSelected,
    this.selectedAgentName,
  });

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: Column(
        children: [
          _buildHeader(context),
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                _buildNavigationItem(context, 0, Icons.dashboard, 'Dashboard'),
                _buildNavigationItem(context, 1, Icons.smart_toy, 'AI Agents'),
                _buildNavigationItem(
                  context,
                  2,
                  Icons.add_circle,
                  'Create Agent',
                ),
                _buildNavigationItem(
                  context,
                  3,
                  Icons.chat_bubble,
                  'Chat',
                  subtitle: selectedAgentName != null
                      ? 'with $selectedAgentName'
                      : 'Select an agent first',
                ),
                const Divider(height: 32),
                _buildNavigationItem(context, -1, Icons.settings, 'Settings'),
                _buildNavigationItem(
                  context,
                  -2,
                  Icons.help_outline,
                  'Help & Support',
                ),
              ],
            ),
          ),
          _buildFooter(context),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Consumer<AuthService>(
      builder: (context, auth, child) {
        return UserAccountsDrawerHeader(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Theme.of(context).colorScheme.primary,
                Theme.of(context).colorScheme.secondary,
              ],
            ),
          ),
          currentAccountPicture: CircleAvatar(
            backgroundColor: Colors.white,
            child: Text(
              auth.user?.username.substring(0, 1).toUpperCase() ?? 'U',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
          accountName: Text(
            auth.user?.displayName ?? 'User',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
          ),
          accountEmail: Text(
            auth.user?.email ?? auth.user?.username ?? '',
            style: const TextStyle(fontSize: 14),
          ),
        );
      },
    );
  }

  Widget _buildNavigationItem(
    BuildContext context,
    int index,
    IconData icon,
    String title, {
    String? subtitle,
  }) {
    final isSelected = selectedIndex == index;

    return ListTile(
      leading: Icon(
        icon,
        color: isSelected
            ? Theme.of(context).colorScheme.primary
            : Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
      ),
      title: Text(
        title,
        style: TextStyle(
          color: isSelected
              ? Theme.of(context).colorScheme.primary
              : Theme.of(context).colorScheme.onSurface,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
        ),
      ),
      subtitle: subtitle != null
          ? Text(
              subtitle,
              style: TextStyle(
                fontSize: 12,
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
            )
          : null,
      selected: isSelected,
      selectedTileColor: Theme.of(
        context,
      ).colorScheme.primaryContainer.withOpacity(0.3),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      onTap: () {
        Navigator.of(context).pop();
        if (index >= 0) {
          onItemSelected(index);
        } else {
          _handleSpecialItems(context, index);
        }
      },
    );
  }

  Widget _buildFooter(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
          ),
        ),
      ),
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text('Sign Out', style: TextStyle(color: Colors.red)),
            onTap: () {
              Navigator.of(context).pop();
              _showLogoutDialog(context);
            },
          ),
          const SizedBox(height: 8),
          Text(
            'Version ${AppConfig.version}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
            ),
          ),
        ],
      ),
    );
  }

  void _handleSpecialItems(BuildContext context, int index) {
    switch (index) {
      case -1: // Settings
        // TODO: Navigate to settings
        break;
      case -2: // Help & Support
        // TODO: Navigate to help
        break;
    }
  }

  void _showLogoutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              Provider.of<AuthService>(context, listen: false).logout();
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );
  }
}
