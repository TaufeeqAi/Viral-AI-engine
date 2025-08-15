// lib/screens/dashboard/dashboard_screen.dart

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/auth_service.dart';
import '../../services/api_service.dart';
import '../../models/agent_config.dart';
import '../../widgets/common/loading_overlay.dart';
import '../../widgets/dashboard/stats_card.dart';
import '../../widgets/dashboard/quick_actions.dart';
import '../../widgets/dashboard/recent_agents.dart';
import '../../widgets/dashboard/activity_chart.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isLoading = true;
  List<AgentConfig> _agents = [];
  Map<String, dynamic> _stats = {};

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
    });

    try {
      final authService = Provider.of<AuthService>(context, listen: false);
      final apiService = ApiService(authService.token!);

      _agents = await apiService.getAgents();
      _calculateStats();
    } catch (e) {
      // Handle error
      debugPrint('Error loading dashboard data: $e');
    } finally {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _calculateStats() {
    _stats = {
      'totalAgents': _agents.length,
      'activeAgents': _agents.where((agent) => agent.id != null).length,
      'totalChats': _agents.length * 15, // Mock data
      'avgResponseTime': '2.3s', // Mock data
    };
  }

  @override
  Widget build(BuildContext context) {
    return LoadingOverlay(
      isLoading: _isLoading,
      child: RefreshIndicator(
        onRefresh: _loadDashboardData,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildWelcomeSection(),
              const SizedBox(height: 24),
              _buildStatsSection(),
              const SizedBox(height: 24),
              _buildQuickActions(),
              const SizedBox(height: 24),
              _buildContentGrid(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWelcomeSection() {
    return Consumer<AuthService>(
      builder: (context, auth, child) {
        final now = DateTime.now();
        final hour = now.hour;
        String greeting = 'Good morning';
        if (hour >= 12 && hour < 17) {
          greeting = 'Good afternoon';
        } else if (hour >= 17) {
          greeting = 'Good evening';
        }

        return Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Theme.of(context).colorScheme.primary,
                Theme.of(context).colorScheme.secondary,
              ],
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$greeting, ${auth.user?.displayName ?? 'User'}!',
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Welcome back to your AI agent management console.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white.withOpacity(0.9),
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(
                  Icons.psychology,
                  size: 40,
                  color: Colors.white,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStatsSection() {
    return Row(
      children: [
        Expanded(
          child: StatsCard(
            title: 'Total Agents',
            value: _stats['totalAgents']?.toString() ?? '0',
            icon: Icons.smart_toy,
            color: Colors.blue,
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: StatsCard(
            title: 'Active Agents',
            value: _stats['activeAgents']?.toString() ?? '0',
            icon: Icons.play_circle_fill,
            color: Colors.green,
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: StatsCard(
            title: 'Total Chats',
            value: _stats['totalChats']?.toString() ?? '0',
            icon: Icons.chat_bubble,
            color: Colors.orange,
          ),
        ),
        if (MediaQuery.of(context).size.width > 800) ...[
          const SizedBox(width: 16),
          Expanded(
            child: StatsCard(
              title: 'Avg Response',
              value: _stats['avgResponseTime']?.toString() ?? '0s',
              icon: Icons.speed,
              color: Colors.purple,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildQuickActions() {
    return QuickActions(
      onCreateAgent: () {
        // TODO: Navigate to create agent
      },
      onViewAgents: () {
        // TODO: Navigate to agents list
      },
      onStartChat: () {
        // TODO: Navigate to chat
      },
    );
  }

  Widget _buildContentGrid() {
    if (MediaQuery.of(context).size.width > 1200) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: RecentAgents(agents: _agents.take(5).toList()),
          ),
          const SizedBox(width: 16),
          Expanded(child: ActivityChart()),
        ],
      );
    } else {
      return Column(
        children: [
          RecentAgents(agents: _agents.take(5).toList()),
          const SizedBox(height: 24),
          ActivityChart(),
        ],
      );
    }
  }
}
