// lib/widgets/agents/agent_search_bar.dart

import 'package:flutter/material.dart';

class AgentSearchBar extends StatefulWidget {
  final Function(String) onSearchChanged;
  final Function(String) onSortChanged;
  final String currentSort;
  final bool isAscending;

  const AgentSearchBar({
    super.key,
    required this.onSearchChanged,
    required this.onSortChanged,
    required this.currentSort,
    required this.isAscending,
  });

  @override
  State<AgentSearchBar> createState() => _AgentSearchBarState();
}

class _AgentSearchBarState extends State<AgentSearchBar> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'Search agents...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchController.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                        widget.onSearchChanged('');
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            onChanged: widget.onSearchChanged,
          ),
        ),
        const SizedBox(width: 12),
        PopupMenuButton<String>(
          icon: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.sort),
              Icon(
                widget.isAscending ? Icons.arrow_upward : Icons.arrow_downward,
                size: 16,
              ),
            ],
          ),
          tooltip: 'Sort agents',
          itemBuilder: (context) => [
            PopupMenuItem(
              value: 'name',
              child: Row(
                children: [
                  Icon(
                    Icons.text_fields,
                    color: widget.currentSort == 'name'
                        ? Theme.of(context).colorScheme.primary
                        : null,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Name',
                    style: TextStyle(
                      color: widget.currentSort == 'name'
                          ? Theme.of(context).colorScheme.primary
                          : null,
                      fontWeight: widget.currentSort == 'name'
                          ? FontWeight.w600
                          : FontWeight.normal,
                    ),
                  ),
                ],
              ),
            ),
            PopupMenuItem(
              value: 'provider',
              child: Row(
                children: [
                  Icon(
                    Icons.cloud,
                    color: widget.currentSort == 'provider'
                        ? Theme.of(context).colorScheme.primary
                        : null,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Provider',
                    style: TextStyle(
                      color: widget.currentSort == 'provider'
                          ? Theme.of(context).colorScheme.primary
                          : null,
                      fontWeight: widget.currentSort == 'provider'
                          ? FontWeight.w600
                          : FontWeight.normal,
                    ),
                  ),
                ],
              ),
            ),
            PopupMenuItem(
              value: 'created',
              child: Row(
                children: [
                  Icon(
                    Icons.schedule,
                    color: widget.currentSort == 'created'
                        ? Theme.of(context).colorScheme.primary
                        : null,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Created',
                    style: TextStyle(
                      color: widget.currentSort == 'created'
                          ? Theme.of(context).colorScheme.primary
                          : null,
                      fontWeight: widget.currentSort == 'created'
                          ? FontWeight.w600
                          : FontWeight.normal,
                    ),
                  ),
                ],
              ),
            ),
          ],
          onSelected: widget.onSortChanged,
        ),
      ],
    );
  }
}
