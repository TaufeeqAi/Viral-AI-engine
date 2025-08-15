// lib/screens/agents/agent_list_screen.dart
import 'package:cyrene_ui/config/app_config.dart';
import 'package:cyrene_ui/screens/agents/agent_detail_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/auth_service.dart';
import '../../services/api_service.dart';
import '../../models/agent_config.dart';
import '../../widgets/common/loading_overlay.dart';
import '../../widgets/common/empty_state.dart';
import '../../widgets/agents/agent_card.dart';
import '../../widgets/agents/agent_search_bar.dart';

class AgentListScreen extends StatefulWidget {
  final Function(String, String) onAgentSelected;

  const AgentListScreen({super.key, required this.onAgentSelected});

  @override
  State<AgentListScreen> createState() => _AgentListScreenState();
}

class _AgentListScreenState extends State<AgentListScreen> {
  bool _isLoading = true;
  List<AgentConfig> _agents = [];
  List<AgentConfig> _filteredAgents = [];
  String _searchQuery = '';
  String _sortBy = 'name';
  bool _isAscending = true;

  @override
  void initState() {
    super.initState();
    _loadAgents();
  }

  Future<void> _loadAgents() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final authService = Provider.of<AuthService>(context, listen: false);
      final apiService = ApiService(authService.token!);

      _agents = await apiService.getAgents();
      _filterAndSortAgents();
    } catch (e) {
      _showErrorSnackBar('Failed to load agents: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _filterAndSortAgents() {
    _filteredAgents = _agents.where((agent) {
      return agent.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          agent.modelProvider.toLowerCase().contains(
            _searchQuery.toLowerCase(),
          );
    }).toList();

    _filteredAgents.sort((a, b) {
      int comparison;
      switch (_sortBy) {
        case 'name':
          comparison = a.name.compareTo(b.name);
          break;
        case 'provider':
          comparison = a.modelProvider.compareTo(b.modelProvider);
          break;
        case 'created':
          comparison = (a.createdAt ?? DateTime.now()).compareTo(
            b.createdAt ?? DateTime.now(),
          );
          break;
        default:
          comparison = a.name.compareTo(b.name);
      }
      return _isAscending ? comparison : -comparison;
    });
  }

  void _onSearchChanged(String query) {
    setState(() {
      _searchQuery = query;
      _filterAndSortAgents();
    });
  }

  void _onSortChanged(String sortBy) {
    setState(() {
      if (_sortBy == sortBy) {
        _isAscending = !_isAscending;
      } else {
        _sortBy = sortBy;
        _isAscending = true;
      }
      _filterAndSortAgents();
    });
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(context).colorScheme.error,
      ),
    );
  }

  Future<void> _deleteAgent(AgentConfig agent) async {
    if (agent.name.toLowerCase() == 'cyrene') {
      _showErrorSnackBar("The default Cyrene agent cannot be deleted.");
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Agent'),
        content: Text('Are you sure you want to delete "${agent.name}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true && agent.id != null) {
      try {
        final authService = Provider.of<AuthService>(context, listen: false);
        final apiService = ApiService(authService.token!);

        await apiService.deleteAgent(agent.id!);
        await _loadAgents(); // Refresh the list

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Agent deleted successfully')),
        );
      } catch (e) {
        _showErrorSnackBar('Failed to delete agent: $e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return LoadingOverlay(
      isLoading: _isLoading,
      child: Column(
        children: [
          _buildHeader(),
          Expanded(child: _buildContent()),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          AgentSearchBar(
            onSearchChanged: _onSearchChanged,
            onSortChanged: _onSortChanged,
            currentSort: _sortBy,
            isAscending: _isAscending,
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${_filteredAgents.length} agent${_filteredAgents.length != 1 ? 's' : ''}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _loadAgents,
                tooltip: 'Refresh',
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    if (_filteredAgents.isEmpty && !_isLoading) {
      return EmptyState(
        icon: Icons.smart_toy_outlined,
        title: _searchQuery.isEmpty ? 'No agents yet' : 'No agents found',
        subtitle: _searchQuery.isEmpty
            ? 'Create your first AI agent to get started'
            : 'Try adjusting your search criteria',
        action: _searchQuery.isEmpty
            ? ElevatedButton.icon(
                onPressed: () {
                  // TODO: Navigate to create agent
                },
                icon: const Icon(Icons.add),
                label: const Text('Create Agent'),
              )
            : null,
      );
    }

    return RefreshIndicator(onRefresh: _loadAgents, child: _buildAgentGrid());
  }

  Widget _buildAgentGrid() {
    final crossAxisCount = _getCrossAxisCount();

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        childAspectRatio: 0.8,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: _filteredAgents.length,
      itemBuilder: (context, index) {
        final agent = _filteredAgents[index];
        return AgentCard(
          agent: agent,
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => AgentDetailScreen(agent: agent),
              ),
            );
          },
          onDelete: () => _deleteAgent(agent),
          onEdit: () {
            Navigator.pushNamed(context, Routes.editAgent);
          },
        );
      },
    );
  }

  int _getCrossAxisCount() {
    final width = MediaQuery.of(context).size.width;
    if (width > 1200) return 4;
    if (width > 800) return 3;
    if (width > 600) return 2;
    return 1;
  }
}
