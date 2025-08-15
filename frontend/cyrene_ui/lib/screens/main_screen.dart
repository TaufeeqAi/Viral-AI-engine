import 'package:cyrene_ui/screens/profile/profile_screen.dart';
import 'package:cyrene_ui/services/api_service.dart';
import 'package:cyrene_ui/services/chat_service.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../config/app_config.dart';
import '../models/chat_session.dart';
import 'agents/agent_list_screen.dart';
import 'agents/create_agent_screen.dart';
import 'chat/chat_screen.dart';
import 'dashboard/dashboard_screen.dart';
import '../widgets/common/custom_drawer.dart';
import 'package:cyrene_ui/widgets/chat/chat_history_sidebar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'settings/settings_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> with TickerProviderStateMixin {
  int _selectedIndex = 0;
  String? _selectedAgentId;
  String? _selectedAgentName;
  String? _currentSessionId;
  late TabController _tabController;
  bool _isChatHistorySidebarExpanded = false;
  List<ChatSession> _chatSessions = [];

  final List<NavigationItem> _navigationItems = [
    NavigationItem(
      icon: Icons.dashboard_outlined,
      selectedIcon: Icons.dashboard,
      label: 'Dashboard',
    ),
    NavigationItem(
      icon: Icons.smart_toy_outlined,
      selectedIcon: Icons.smart_toy,
      label: 'Agents',
    ),
    NavigationItem(
      icon: Icons.add_circle_outline,
      selectedIcon: Icons.add_circle,
      label: 'Create',
    ),
    NavigationItem(
      icon: Icons.chat_bubble_outline,
      selectedIcon: Icons.chat_bubble,
      label: 'Chat',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _loadLastTabIndex();
    _tabController = TabController(
      length: _navigationItems.length,
      vsync: this,
    );
    _initializeDefaultAgent();
    _loadChatSessions();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _initializeDefaultAgent() async {
    final authService = Provider.of<AuthService>(context, listen: false);
    final apiService = ApiService(authService.token!);
    final agents = await apiService.getAgents();

    if (agents.isEmpty) return;

    final defaultAgent = agents.firstWhere(
      (a) => a.name.toLowerCase() == 'cyrene',
      orElse: () => agents.first,
    );

    setState(() {
      _selectedAgentId = defaultAgent.id;
      _selectedAgentName = defaultAgent.name;
    });
  }

  Future<void> _loadChatSessions() async {
    try {
      final authService = Provider.of<AuthService>(context, listen: false);
      final apiService = ChatService(authService.token!);
      final sessions = await apiService.getAllChatSessions();

      setState(() {
        _chatSessions = sessions;
      });
    } catch (e) {
      debugPrint('Error loading chat sessions: $e');
    }
  }

  void _loadLastTabIndex() async {
    final prefs = await SharedPreferences.getInstance();
    final savedIndex = prefs.getInt('last_tab_index') ?? 0;
    setState(() {
      _selectedIndex = savedIndex;
      _tabController.index = savedIndex;
    });
  }

  void _onAgentSelected(String agentId, String agentName) {
    setState(() {
      _selectedAgentId = agentId;
      _selectedAgentName = agentName;
      _selectedIndex = 3;
      _tabController.animateTo(3);
      _currentSessionId = null; // Start new session
    });
  }

  void _onChatSessionSelected(ChatSession session) {
    setState(() {
      _selectedAgentId = session.agentId;
      _currentSessionId = session.id;
      _selectedIndex = 3;
      _tabController.animateTo(3);
    });
  }

  void _onNavigationTapped(int index) async {
    if (index == 3 && _selectedAgentId == null) {
      _showSelectAgentDialog();
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    prefs.setInt('last_tab_index', index);

    setState(() {
      _selectedIndex = index;
      _tabController.animateTo(index);
    });

    // Auto-expand sidebar when navigating to chat on desktop
    if (index == 3 && MediaQuery.of(context).size.width > 800) {
      setState(() {
        _isChatHistorySidebarExpanded = true;
      });
    }
  }

  void _toggleChatHistorySidebar() {
    setState(() {
      _isChatHistorySidebarExpanded = !_isChatHistorySidebarExpanded;
    });
  }

  void _showSelectAgentDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('No Agent Selected'),
        content: const Text(
          'Please select an agent from the Agents tab first.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDesktop = MediaQuery.of(context).size.width > 800;
    final isMobile = MediaQuery.of(context).size.width <= 600;

    return Scaffold(
      body: Row(
        children: [
          // Navigation Rail for larger screens
          if (isDesktop) _buildNavigationRail(),

          // Chat History Sidebar (Desktop only, when in chat)
          if (isDesktop && _selectedIndex == 3 && _isChatHistorySidebarExpanded)
            ChatHistorySidebar(
              chatSessions: _chatSessions,
              currentSessionId: _currentSessionId,
              onSessionSelected: _onChatSessionSelected,
              onNewChat: () {
                setState(() {
                  _currentSessionId = null;
                });
              },
              onClose: _toggleChatHistorySidebar,
            ),

          // Main content
          Expanded(
            child: Column(
              children: [
                _buildAppBar(),
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    physics: const NeverScrollableScrollPhysics(),
                    children: [
                      const DashboardScreen(),
                      AgentListScreen(onAgentSelected: _onAgentSelected),
                      const CreateAgentScreen(),
                      ChatScreen(
                        agentId: _selectedAgentId,
                        agentName: _selectedAgentName,
                        sessionId: _currentSessionId,
                        showAllHistory: true,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),

      // Bottom Navigation for smaller screens
      bottomNavigationBar: !isDesktop ? _buildBottomNavigationBar() : null,

      // Drawer for mobile (with chat history)
      drawer: isMobile
          ? CustomDrawer(
              selectedIndex: _selectedIndex,
              onItemSelected: _onNavigationTapped,
              selectedAgentName: _selectedAgentName,
              // chatSessions: _chatSessions,
              // currentSessionId: _currentSessionId,
              // onSessionSelected: _onChatSessionSelected,
            )
          : null,
    );
  }

  Widget _buildAppBar() {
    final isDesktop = MediaQuery.of(context).size.width > 800;
    final isMobile = MediaQuery.of(context).size.width <= 600;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
          ),
        ),
      ),
      child: Row(
        children: [
          // Menu button for mobile
          if (isMobile)
            Builder(
              builder: (context) => IconButton(
                icon: const Icon(Icons.menu),
                onPressed: () => Scaffold.of(context).openDrawer(),
              ),
            ),

          // Chat history toggle for desktop (only in chat view)
          if (isDesktop && _selectedIndex == 3)
            IconButton(
              icon: Icon(
                _isChatHistorySidebarExpanded ? Icons.menu_open : Icons.menu,
              ),
              onPressed: _toggleChatHistorySidebar,
              tooltip: _isChatHistorySidebarExpanded
                  ? 'Hide chat history'
                  : 'Show chat history',
            ),

          Text(
            _getScreenTitle(),
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
          ),

          // Current agent indicator
          if (_selectedIndex == 3 && _selectedAgentName != null)
            Container(
              margin: const EdgeInsets.only(left: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                _selectedAgentName!,
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                  fontWeight: FontWeight.w500,
                  fontSize: 12,
                ),
              ),
            ),

          const Spacer(),

          // User menu
          _buildUserMenu(),
        ],
      ),
    );
  }

  Widget _buildNavigationRail() {
    return Container(
      width: _isChatHistorySidebarExpanded && _selectedIndex == 3 ? 72 : 80,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          right: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
          ),
        ),
      ),
      child: NavigationRail(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _onNavigationTapped,
        labelType: _isChatHistorySidebarExpanded && _selectedIndex == 3
            ? NavigationRailLabelType.none
            : NavigationRailLabelType.selected,
        destinations: _navigationItems
            .map(
              (item) => NavigationRailDestination(
                icon: Icon(item.icon),
                selectedIcon: Icon(item.selectedIcon),
                label: Text(item.label),
              ),
            )
            .toList(),
      ),
    );
  }

  Widget _buildBottomNavigationBar() {
    return NavigationBar(
      selectedIndex: _selectedIndex,
      onDestinationSelected: _onNavigationTapped,
      destinations: _navigationItems
          .map(
            (item) => NavigationDestination(
              icon: Icon(item.icon),
              selectedIcon: Icon(item.selectedIcon),
              label: item.label,
            ),
          )
          .toList(),
    );
  }

  Widget _buildUserMenu() {
    return Consumer<AuthService>(
      builder: (context, auth, child) {
        return PopupMenuButton<String>(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircleAvatar(
                radius: 16,
                backgroundColor: Theme.of(context).colorScheme.primary,
                child: Text(
                  auth.user?.username.substring(0, 1).toUpperCase() ?? 'U',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              if (MediaQuery.of(context).size.width > 600)
                Text(
                  auth.user?.displayName ?? 'User',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              const Icon(Icons.arrow_drop_down),
            ],
          ),
          itemBuilder: (context) => [
            PopupMenuItem(
              value: 'profile',
              child: ListTile(
                leading: const Icon(Icons.person),
                title: const Text('Profile'),
                contentPadding: EdgeInsets.zero,
              ),
            ),
            PopupMenuItem(
              value: 'settings',
              child: ListTile(
                leading: const Icon(Icons.settings),
                title: const Text('Settings'),
                contentPadding: EdgeInsets.zero,
              ),
            ),
            const PopupMenuDivider(),
            PopupMenuItem(
              value: 'logout',
              child: ListTile(
                leading: const Icon(Icons.logout, color: Colors.red),
                title: const Text(
                  'Sign Out',
                  style: TextStyle(color: Colors.red),
                ),
                contentPadding: EdgeInsets.zero,
              ),
            ),
          ],
          onSelected: (value) async {
            switch (value) {
              case 'profile':
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ProfileScreen()),
                );
                break;
              case 'settings':
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const SettingsScreen()),
                );
                break;
              case 'logout':
                await auth.logout();
                if (context.mounted) {
                  Navigator.of(context).pushReplacementNamed(Routes.login);
                }
                break;
            }
          },
        );
      },
    );
  }

  String _getScreenTitle() {
    switch (_selectedIndex) {
      case 0:
        return 'Dashboard';
      case 1:
        return 'AI Agents';
      case 2:
        return 'Create Agent';
      case 3:
        return 'Chat';
      default:
        return AppConfig.appName;
    }
  }
}

class NavigationItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;

  NavigationItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });
}
