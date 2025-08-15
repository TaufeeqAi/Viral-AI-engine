import 'package:cyrene_ui/models/tool_model.dart';
import 'package:flutter/material.dart';

class ToolToggleTile extends StatelessWidget {
  final AgentTool tool;
  final bool enabled;
  final ValueChanged<bool> onToggle;

  const ToolToggleTile({
    super.key,
    required this.tool,
    required this.enabled,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return SwitchListTile(
      title: Text(tool.toolDetails?.name ?? "Unnamed Tool"),
      subtitle: Text(tool.toolDetails?.description ?? ""),
      value: enabled,
      onChanged: onToggle,
    );
  }
}
