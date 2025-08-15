import 'dart:convert';

import 'package:cyrene_ui/models/tool_model.dart';

class AgentConfig {
  final String? id;
  final String name;
  final String? userId;
  final bool isActive;
  final String modelProvider;
  final String? system;
  final List<String>? bio;
  final List<String>? lore;
  final List<String>? knowledgeAreas;
  final List<dynamic>? messageExamples; // Changed to a single list of messages
  final String? style; // Changed to a String
  final Map<String, dynamic> settings;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  List<AgentTool>? tools;
  final String? avatarUrl;
  final int totalSessions;
  final DateTime? lastUsed;

  AgentConfig({
    this.id,
    this.isActive = true,
    this.avatarUrl,
    this.totalSessions = 0,
    this.lastUsed,
    this.userId,
    required this.name,
    required this.modelProvider,
    this.system,
    this.bio,
    this.lore,
    this.knowledgeAreas,
    this.messageExamples,
    this.style,
    required this.settings,
    this.createdAt,
    this.updatedAt,
    this.tools,
  });

  /// Factory constructor to create an AgentConfig from a JSON map.
  factory AgentConfig.fromJson(Map<String, dynamic> json) {
    return AgentConfig(
      id: json['id'],
      userId: json['user_id'],
      isActive: json['is_active'] ?? true,
      avatarUrl: json['avatar_url'],
      totalSessions: json['total_sessions'] ?? 0,
      lastUsed: json['last_used'] != null
          ? DateTime.parse(json['last_used'])
          : null,
      name: json['name'],
      modelProvider: json['modelProvider'],
      system: json['system'],
      bio: json['bio'] != null ? List<String>.from(json['bio']) : null,
      lore: json['lore'] != null ? List<String>.from(json['lore']) : null,
      knowledgeAreas: json['knowledgeAreas'] != null
          ? List<String>.from(json['knowledgeAreas'])
          : null,
      // Parse messageExamples as a simple list.
      messageExamples: json['messageExamples'] != null
          ? List<dynamic>.from(json['messageExamples'])
          : null,
      style: json['style'] is String
          ? json['style'] as String
          : jsonEncode(json['style']),
      settings: json['settings'] ?? {},
      createdAt: json['createdAt'] != null
          ? DateTime.parse(json['createdAt'])
          : null,
      updatedAt: json['updatedAt'] != null
          ? DateTime.parse(json['updatedAt'])
          : null,
      tools: json['tools'] != null
          ? List<AgentTool>.from(
              json['tools'].map((t) => AgentTool.fromJson(t)),
            )
          : null,
    );
  }

  /// Converts the AgentConfig instance to a JSON map.
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'user_id': userId,
      'is_active': isActive,
      'avatar_url': avatarUrl,
      'total_sessions': totalSessions,
      'last_used': lastUsed?.toIso8601String(),
      'modelProvider': modelProvider,
      'system': system,
      'bio': bio,
      'lore': lore,
      'knowledgeAreas': knowledgeAreas,
      'messageExamples': messageExamples,
      'style': style,
      'settings': settings,
      'createdAt': createdAt?.toIso8601String(),
      'updatedAt': updatedAt?.toIso8601String(),
      'tools': tools?.map((t) => t.toJson()).toList(),
    };
  }

  /// Creates a new AgentConfig instance with updated values.
  AgentConfig copyWith({
    String? id,
    String? name,
    String? modelProvider,
    String? system,
    List<String>? bio,
    List<String>? lore,
    List<String>? knowledgeAreas,
    List<dynamic>? messageExamples,
    String? style,
    Map<String, dynamic>? settings,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? userId,
    bool? isActive,
    String? avatarUrl,
    int? totalSessions,
    dynamic lastUsed,
  }) {
    return AgentConfig(
      id: id ?? this.id,
      name: name ?? this.name,
      userId: userId ?? this.userId,
      isActive: isActive ?? this.isActive,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      totalSessions: totalSessions!,
      lastUsed: lastUsed?.toIso8601String() ?? this.lastUsed,
      modelProvider: modelProvider ?? this.modelProvider,
      system: system ?? this.system,
      bio: bio ?? this.bio,
      lore: lore ?? this.lore,
      knowledgeAreas: knowledgeAreas ?? this.knowledgeAreas,
      messageExamples: messageExamples ?? this.messageExamples,
      style: style ?? this.style,
      settings: settings ?? this.settings,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
