class Tool {
  final String? id;
  final String name;
  final String? description;
  final Map<String, dynamic>? config;

  Tool({this.id, required this.name, this.description, this.config});

  factory Tool.fromJson(Map<String, dynamic> json) {
    return Tool(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      config: json['config'] != null
          ? Map<String, dynamic>.from(json['config'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'config': config,
    };
  }
}

class AgentTool {
  final String? toolId;
  bool isEnabled;
  final Tool? toolDetails;

  AgentTool({this.toolId, required this.isEnabled, this.toolDetails});

  factory AgentTool.fromJson(Map<String, dynamic> json) {
    return AgentTool(
      toolId: json['tool_id'],
      isEnabled: json['is_enabled'] ?? false,
      toolDetails: json['tool_details'] != null
          ? Tool.fromJson(json['tool_details'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'tool_id': toolId,
      'is_enabled': isEnabled,
      'tool_details': toolDetails?.toJson(),
    };
  }
}
