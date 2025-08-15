// create_agent_screen.dart
import 'dart:math';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import '../../services/auth_service.dart';
import '../../services/api_service.dart';
import '../../config/app_config.dart';
import '../../widgets/common/custom_text_field.dart';
import '../../widgets/common/gradient_button.dart';
import '../../widgets/common/loading_overlay.dart';

class CreateAgentScreen extends StatefulWidget {
  const CreateAgentScreen({super.key});

  @override
  State<CreateAgentScreen> createState() => _CreateAgentScreenState();
}

class _CreateAgentScreenState extends State<CreateAgentScreen> {
  final _formKey = GlobalKey<FormState>();

  // Form controllers
  final _nameController = TextEditingController();
  final _secretsController = TextEditingController();
  final _systemController = TextEditingController();
  final _bioController = TextEditingController();
  final _loreController = TextEditingController();
  final _knowledgeAreasController = TextEditingController();
  final _messageExamplesController = TextEditingController();
  final _styleController = TextEditingController();

  bool _isLoading = false;
  String _selectedProvider = 'Groq';
  String _llmModel = AppConfig.defaultModel;
  double _temperature = AppConfig.defaultTemperature;
  int _maxTokens = AppConfig.defaultMaxTokens;

  final List<String> _availableProviders = [
    'Groq',
    'Anthropic',
    "OpenAI",
    "Google",
  ];

  final Map<String, List<String>> _providerModels = {
    'openai': [
      'gpt-3.5-turbo',
      'gpt-4',
      'gpt-4-32k', // Older, but still might be in use
      'gpt-4-turbo', // Alias for latest turbo model
      'gpt-4o',
      'gpt-4o-mini',
      'gpt-4.1',
      'gpt-4.1-mini',
      'gpt-4.1-nano',
    ],
    'anthropic': [
      'claude-3-haiku-20240307',
      'claude-3-sonnet-20240229',
      'claude-3-opus-20240229',
      'claude-3-5-sonnet-20240620',
      'claude-3-7-sonnet-20250219', // Updated to include full date
      'claude-sonnet-4-20250514',
      'claude-opus-4-20250514',
      'claude-opus-4-1-20250805', // Latest Opus 4.1
      'claude-3-5-haiku-20241022', // Added 3.5 Haiku
    ],
    'groq': [
      'llama3-8b-8192',
      'llama3-70b-8192',
      'llama-3.1-8b-instant',
      'llama-3.3-70b-versatile',
      'gemma2-9b-it',
      'meta-llama/llama-4-scout-17b-16e-instruct',
      'meta-llama/llama-4-maverick-17b-128e-instruct',
      'meta-llama/llama-guard-4-12b',
      'moonshotai/kimi-k2-instruct',
      'qwen/qwen3-32b',
      'deepseek-r1-distill-llama-70b',
      'gpt-oss-20B', // OpenAI open models on Groq
      'gpt-oss-120B', // OpenAI open models on Groq
    ],
    'google': [
      'gemini-1.5-pro',
      'gemini-2.5-flash',
      'gemini-2.5-pro',
      'gemini-2.5-flash-lite',
      'gemini-live-2.5-flash-preview',
      'gemini-2.5-flash-preview-native-audio-dialog',
      // 'gemma-2-9b-it' is also a Google model, but often listed under Groq for GroqCloud
    ],
  };

  final Map<String, int> _modelMaxTokenLimits = {
    // OpenAI Models (These are typically context window limits, not just output)
    'gpt-3.5-turbo': 16385,
    'gpt-4': 8192,
    'gpt-4-32k': 32768,
    'gpt-4-turbo': 128000,
    'gpt-4o': 128000,
    'gpt-4o-mini': 128000,
    'gpt-4.1': 1000000, // 1M tokens context
    'gpt-4.1-mini': 1000000,
    'gpt-4.1-nano': 1000000,

    // Anthropic Models (These are context window limits, consistently 200K for Claude 3/4)
    'claude-3-haiku-20240307': 200000,
    'claude-3-sonnet-20240229': 200000,
    'claude-3-opus-20240229': 200000,
    'claude-3-5-sonnet-20240620': 200000,
    'claude-3-7-sonnet-20250219': 200000,
    'claude-sonnet-4-20250514': 200000,
    'claude-opus-4-20250514': 200000,
    'claude-opus-4-1-20250805': 200000,
    'claude-3-5-haiku-20241022': 200000,

    // Groq Models (These are context window limits)
    'llama3-8b-8192': 8192,
    'llama3-70b-8192': 8192,
    'llama-3.1-8b-instant': 128000,
    'llama-3.3-70b-versatile': 128000,
    'gemma2-9b-it': 8192,
    'meta-llama/llama-4-scout-17b-16e-instruct': 128000,
    'meta-llama/llama-4-maverick-17b-128e-instruct': 128000,
    'meta-llama/llama-guard-4-12b': 128000,
    'moonshotai/kimi-k2-instruct': 131072,
    'qwen/qwen3-32b': 131072,
    'deepseek-r1-distill-llama-70b': 128000,
    'gpt-oss-20B': 128000,
    'gpt-oss-120B': 128000,

    // Google Models (These are context window limits)
    'gemini-1.5-pro': 1048576, // 1M tokens
    'gemini-2.5-flash': 1048576, // 1M tokens
    'gemini-2.5-pro': 1048576, // 1M tokens
    'gemini-2.5-flash-lite': 1048576,
    'gemini-live-2.5-flash-preview': 1048576,
    'gemini-2.5-flash-preview-native-audio-dialog': 128000,
  };

  final Map<String, int> _modelMaxOutputLimits = {
    // OpenAI Models
    'gpt-3.5-turbo': 4096,
    'gpt-4': 4096,
    'gpt-4-32k': 4096,
    'gpt-4-turbo':
        4096, // Default, can be higher up to context window minus prompt
    'gpt-4o': 4096, // Default, can be higher up to context window minus prompt
    'gpt-4o-mini': 4096, // Default
    'gpt-4.1': 32768,
    'gpt-4.1-mini': 32768,
    'gpt-4.1-nano': 32768,

    // Anthropic Models
    'claude-3-haiku-20240307': 4096,
    'claude-3-sonnet-20240229':
        8192, // Common default, though some tiers can be higher
    'claude-3-opus-20240229':
        8192, // Common default, though some tiers can be higher
    'claude-3-5-sonnet-20240620': 16000,
    'claude-3-7-sonnet-20250219': 128000,
    'claude-sonnet-4-20250514': 64000,
    'claude-opus-4-20250514': 32000,
    'claude-opus-4-1-20250805': 32000,
    'claude-3-5-haiku-20241022': 8192,

    // Groq Models (often full context for output unless specified)
    'llama3-8b-8192': 8192,
    'llama3-70b-8192': 8192,
    'llama-3.1-8b-instant': 128000,
    'llama-3.3-70b-versatile': 128000,
    'gemma2-9b-it': 8192,
    'meta-llama/llama-4-scout-17b-16e-instruct': 8192,
    'meta-llama/llama-4-maverick-17b-128e-instruct': 8192,
    'meta-llama/llama-guard-4-12b': 128000,
    'moonshotai/kimi-k2-instruct': 131072,
    'qwen/qwen3-32b': 131072,
    'deepseek-r1-distill-llama-70b': 128000,
    'gpt-oss-20B': 128000,
    'gpt-oss-120B': 128000,

    // Google Models
    'gemini-1.5-pro': 65536,
    'gemini-2.5-flash': 65536,
    'gemini-2.5-pro': 65535,
    'gemini-2.5-flash-lite': 65536,
    'gemini-live-2.5-flash-preview': 8192,
    'gemini-2.5-flash-preview-native-audio-dialog': 8000,
  };

  @override
  void dispose() {
    _nameController.dispose();
    _secretsController.dispose();
    _systemController.dispose();
    _bioController.dispose();
    _loreController.dispose();
    _knowledgeAreasController.dispose();
    _messageExamplesController.dispose();
    _styleController.dispose();
    super.dispose();
  }

  /// Sends the agent data to the API to be created.
  Future<void> _createAgent(Map<String, dynamic> agentData) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final authService = Provider.of<AuthService>(context, listen: false);
      final apiService = ApiService(authService.token!);

      print('🚀 Sending agent data to API...');
      final response = await apiService.createAgent(agentData);
      print('✅ Agent created: $response');

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Agent created successfully!')),
      );

      _clearForm();
    } catch (e) {
      print('❌ Failed to create agent: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to create agent: $e'),
          backgroundColor: Theme.of(context).colorScheme.error,
        ),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  /// Clears all the form fields and resets state variables.
  void _clearForm() {
    _nameController.clear();
    _secretsController.clear();
    _systemController.clear();
    _bioController.clear();
    _loreController.clear();
    _knowledgeAreasController.clear();
    _messageExamplesController.clear();
    _styleController.clear();
    setState(() {
      _selectedProvider = 'Groq';
      _llmModel = AppConfig.defaultModel;
      _temperature = AppConfig.defaultTemperature;
      _maxTokens = AppConfig.defaultMaxTokens;
    });
  }

  void _updateModelAndTokenLimits(String provider) {
    final models = _providerModels[provider.toLowerCase()];
    if (models != null && models.isNotEmpty) {
      _llmModel = models.first;
      _maxTokens =
          _modelMaxTokenLimits[_llmModel] ?? AppConfig.defaultMaxTokens;
    }
  }

  int get currentModelMaxTokens =>
      _modelMaxTokenLimits[_llmModel] ?? AppConfig.defaultMaxTokens;

  /// Creates an agent from the data entered in the form.
  Future<void> _createAgentFromForm() async {
    if (!_formKey.currentState!.validate()) return;

    try {
      print('🔍 Parsing secrets...');
      final secrets = _secretsController.text.isNotEmpty
          ? json.decode(_secretsController.text) as Map<String, dynamic>
          : {};

      // 🔧 Normalize telegram_api_id
      if (secrets.containsKey('telegram_api_id')) {
        final apiId = secrets['telegram_api_id'];
        if (apiId is String) {
          print("converting telegramID from string to int");
          final parsed = int.tryParse(apiId);
          if (parsed != null) {
            secrets['telegram_api_id'] = parsed; // ✅ Convert to int
            print("Telegram ID converted to INT");
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: const Text("Telegram API ID must be a valid number."),
                backgroundColor: Theme.of(context).colorScheme.error,
              ),
            );
            return; // ❌ Don't proceed if invalid
          }
        } else if (apiId is! int) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text("Telegram API ID must be a number."),
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
          );
          return;
        }
      }

      // --- FIX: messageExamples should be List[Dict] (flat list, not nested) ---
      print('🔍 Parsing and converting messageExamples...');
      List<dynamic> messageExamples = [];
      if (_messageExamplesController.text.isNotEmpty) {
        final rawExamples =
            json.decode(_messageExamplesController.text) as List<dynamic>;

        // Convert each message to the format: Dict (not wrapped in a list)
        messageExamples = rawExamples.map((item) {
          if (item is Map<String, dynamic>) {
            String content = item['content'] ?? '';

            // If content is a JSON string with "text" field, extract it
            if (content.startsWith('{') && content.contains('"text"')) {
              try {
                final contentObj = json.decode(content) as Map<String, dynamic>;
                content = contentObj['text'] ?? content;
              } catch (e) {
                // If parsing fails, use the original content
              }
            }

            // Return as a simple dictionary (matching what API validation expects)
            return {'user': item['user'] ?? '', 'content': content};
          }
          return item;
        }).toList();
      }

      // --- FIX: `style` should be parsed as JSON object, not kept as string ---
      print('🔍 Validating style JSON string...');
      String? styleString;
      if (_styleController.text.isNotEmpty) {
        try {
          // Validate that it's valid JSON, but keep it as a string (API expects string)
          json.decode(_styleController.text);
          styleString = _styleController.text;
        } catch (e) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Invalid JSON for Style field: $e'),
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
          );
          return;
        }
      }

      final agentData = {
        'name': _nameController.text,
        'modelProvider': _selectedProvider.toLowerCase(),
        'system': _systemController.text.isEmpty
            ? null
            : _systemController.text,
        'bio': _bioController.text.isEmpty
            ? null
            : _bioController.text.split(',').map((e) => e.trim()).toList(),
        'lore': _loreController.text.isEmpty
            ? null
            : _loreController.text.split(',').map((e) => e.trim()).toList(),
        'knowledge': _knowledgeAreasController.text.isEmpty
            ? null
            : _knowledgeAreasController.text
                  .split(',')
                  .map((e) => e.trim())
                  .toList(),
        'messageExamples': messageExamples.isEmpty
            ? null
            : messageExamples, // ✅ Flat list
        'style': styleString, // ✅ Send as parsed JSON object (not string)
        'settings': {
          'model': _llmModel,
          'temperature': _temperature,
          'maxTokens': _maxTokens,
          'secrets': secrets,
        },
      };

      print('📦 Final agent payload (truncated):');
      // Truncate the output for better readability in the console.
      final payloadJson = jsonEncode(agentData);
      print(
        payloadJson.length > 200
            ? payloadJson.substring(0, 200) + '...'
            : payloadJson,
      );

      await _createAgent(agentData);
    } catch (e) {
      print('❌ Error while parsing JSON: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to parse JSON fields: $e'),
          backgroundColor: Theme.of(context).colorScheme.error,
        ),
      );
    }
  }

  /// Handles the process of picking a JSON file and populating the form.
  Future<void> _loadAgentConfigFromFile() async {
    setState(() {
      _isLoading = true;
    });

    try {
      print('📁 Opening file picker...');
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
        withData: true, // ✅ ensures we get file.bytes on Web
      );

      if (result == null) {
        print('⚠️ No file selected');
        return;
      }

      final pickedFile = result.files.single;
      String jsonString;

      if (pickedFile.bytes != null) {
        print('📦 Reading from memory bytes...');
        jsonString = utf8.decode(pickedFile.bytes!);
      } else if (pickedFile.path != null) {
        print('📄 Reading from file path: ${pickedFile.path}');
        jsonString = await File(pickedFile.path!).readAsString();
      } else {
        throw Exception('No readable file data found.');
      }

      print('🧾 Raw JSON string:\n$jsonString');
      final agentConfig = json.decode(jsonString) as Map<String, dynamic>;
      print('✅ Parsed agent config');

      _nameController.text = agentConfig['name'] ?? '';
      _systemController.text = agentConfig['system'] ?? '';
      _bioController.text =
          (agentConfig['bio'] as List<dynamic>?)?.join(', ') ?? '';
      _loreController.text =
          (agentConfig['lore'] as List<dynamic>?)?.join(', ') ?? '';
      _knowledgeAreasController.text =
          (agentConfig['knowledge'] as List<dynamic>?)?.join(', ') ??
          ''; // Changed from 'knowledgeAreas' to 'knowledge'

      final messageExamplesFromConfig = agentConfig['messageExamples'];
      if (messageExamplesFromConfig != null &&
          messageExamplesFromConfig is List) {
        // Handle both nested and flat messageExamples format from file
        final List<dynamic> flattenedForDisplay = [];
        for (var item in messageExamplesFromConfig) {
          if (item is List) {
            flattenedForDisplay.addAll(item);
          } else if (item is Map<String, dynamic>) {
            flattenedForDisplay.add(item);
          }
        }

        // Correct the content format to be a simple string for the UI
        final List<dynamic> messagesWithUserKey = flattenedForDisplay.map((
          message,
        ) {
          if (message is Map<String, dynamic> &&
              message.containsKey('content')) {
            // Ensure content is a string for display
            if (message['content'] is! String) {
              message['content'] = json.encode(message['content']);
            }
          }
          return message;
        }).toList();

        _messageExamplesController.text = json.encode(messagesWithUserKey);
      } else {
        _messageExamplesController.text = '';
      }

      final styleFromConfig = agentConfig['style'];
      if (styleFromConfig != null) {
        // Style is likely a JSON object, so encode it to a string for the text field
        _styleController.text = styleFromConfig is String
            ? styleFromConfig
            : json.encode(styleFromConfig);
      } else {
        _styleController.text = '';
      }

      print('📝 Populated form fields');

      final settings = agentConfig['settings'] as Map<String, dynamic>?;
      if (settings != null) {
        setState(() {
          _selectedProvider = _availableProviders.firstWhere(
            (p) =>
                p.toLowerCase() ==
                (agentConfig['modelProvider'] ?? '').toLowerCase(),
            orElse: () => AppConfig.defaultModelProvider,
          );

          final availableModels =
              _providerModels[_selectedProvider.toLowerCase()] ?? [];
          final loadedModel = settings['model'] ?? AppConfig.defaultModel;

          if (availableModels.contains(loadedModel)) {
            _llmModel = loadedModel;
          } else {
            _llmModel = availableModels.isNotEmpty
                ? availableModels.first
                : AppConfig.defaultModel;
          }

          if (!availableModels.contains(loadedModel)) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    'Model "$loadedModel" not found for provider $_selectedProvider. Defaulting to $_llmModel.',
                  ),
                  backgroundColor: Theme.of(context).colorScheme.error,
                ),
              );
            });
          }

          _temperature =
              (settings['temperature'] as num?)?.toDouble() ??
              AppConfig.defaultTemperature;
          _maxTokens =
              _modelMaxTokenLimits[_llmModel] ?? AppConfig.defaultMaxTokens;
        });

        print('⚙️ Settings loaded: $_llmModel, $_temperature, $_maxTokens');

        final secrets = settings['secrets'] as Map<String, dynamic>?;
        if (secrets != null) {
          _secretsController.text = json.encode(secrets);
          print('🔐 Loaded secrets');
        }
      }

      setState(() {
        _selectedProvider = _availableProviders.firstWhere(
          (p) =>
              p.toLowerCase() ==
              (agentConfig['modelProvider'] ?? '').toLowerCase(),
          orElse: () => AppConfig.defaultModelProvider,
        );
      });
      print('🌐 Provider selected: $_selectedProvider');

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Agent configuration loaded from file!')),
      );
    } catch (e) {
      print('❌ Failed to load or parse agent file: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to load file: $e'),
          backgroundColor: Theme.of(context).colorScheme.error,
        ),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return LoadingOverlay(
      isLoading: _isLoading,
      message: 'Creating agent...',
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              GradientButton(
                onPressed: _isLoading ? null : _loadAgentConfigFromFile,
                gradient: LinearGradient(
                  colors: [
                    Theme.of(context).colorScheme.primary,
                    Theme.of(context).colorScheme.secondary,
                  ],
                ),
                height: 56,
                child: _isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : const Text(
                        'Load from JSON File',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
              ),
              const SizedBox(height: 24),
              _buildAgentDetailsSection(),
              const SizedBox(height: 24),
              _buildLLMSettingsSection(),
              const SizedBox(height: 24),
              _buildCreateButton(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAgentDetailsSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Agent Details',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _nameController,
              label: 'Agent Name',
              prefixIcon: Icons.person,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Please enter an agent name';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _systemController,
              label: 'System Prompt',
              prefixIcon: Icons.psychology,
              maxLines: 4,
              hintText: 'Define your agent\'s personality and behavior...',
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _bioController,
              label: 'Bio (comma-separated)',
              prefixIcon: Icons.info_outline,
              maxLines: 4,
              hintText:
                  'e.g., "I am an expert in travel, I can provide detailed itineraries."',
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _loreController,
              label: 'Lore (comma-separated)',
              prefixIcon: Icons.menu_book,
              maxLines: 4,
              hintText: 'e.g., "Born from ancient maps, explorer."',
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _knowledgeAreasController,
              label: 'Knowledge Areas (comma-separated)',
              prefixIcon: Icons.lightbulb_outline,
              maxLines: 4,
              hintText: 'e.g., "travel, history, geography, cuisine"',
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _messageExamplesController,
              label: 'Message Examples (JSON Array)',
              prefixIcon: Icons.message,
              maxLines: 6,
              hintText: 'e.g., [{"user": "user1", "content": "hello"}]',
              validator: (value) {
                if (value == null || value.isEmpty) return null;
                try {
                  json.decode(value);
                } catch (e) {
                  return 'Invalid JSON array';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _styleController,
              label: 'Style (JSON String)',
              prefixIcon: Icons.brush,
              maxLines: 4,
              hintText:
                  'e.g., {"all": ["Speaks in a friendly tone.", "Uses simple language."]}',
              validator: (value) {
                if (value == null || value.isEmpty) return null;
                try {
                  json.decode(value);
                } catch (e) {
                  return 'Invalid JSON object';
                }
                return null;
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLLMSettingsSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'LLM Settings',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _selectedProvider,
              decoration: const InputDecoration(
                labelText: 'LLM Provider',
                prefixIcon: Icon(Icons.cloud),
              ),
              items: _availableProviders.map((provider) {
                return DropdownMenuItem(value: provider, child: Text(provider));
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedProvider = value!;
                  _updateModelAndTokenLimits(_selectedProvider);
                });
              },
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value:
                  (_providerModels[_selectedProvider.toLowerCase()] ?? [])
                      .contains(_llmModel)
                  ? _llmModel
                  : null,
              decoration: const InputDecoration(
                labelText: 'LLM Model',
                prefixIcon: Icon(Icons.settings),
              ),
              items: (_providerModels[_selectedProvider.toLowerCase()] ?? [])
                  .map(
                    (model) =>
                        DropdownMenuItem(value: model, child: Text(model)),
                  )
                  .toList(),
              onChanged: (newModel) {
                setState(() {
                  _llmModel = newModel!;
                  _maxTokens =
                      _modelMaxTokenLimits[_llmModel] ??
                      AppConfig.defaultMaxTokens;
                  _maxTokens = min(_maxTokens, currentModelMaxTokens);
                });
              },
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _secretsController,
              label: 'Secrets (JSON)',
              prefixIcon: Icons.key,
              obscureText: false,
              maxLines: 6,
              hintText: '{"groq_api_key": "gsk_..."}',
              validator: (value) {
                if (value == null || value.isEmpty) return null;
                try {
                  json.decode(value);
                } catch (e) {
                  return 'Invalid JSON object';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            Text(
              'Temperature: ${_temperature.toStringAsFixed(1)}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            Slider(
              value: _temperature,
              min: 0.0,
              max: 2.0,
              divisions: 20,
              onChanged: (value) {
                setState(() {
                  _temperature = value;
                });
              },
            ),
            const SizedBox(height: 16),
            Text(
              'Max Tokens: $_maxTokens',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            Slider(
              value: _maxTokens.toDouble(),
              min: 100,
              max: (_modelMaxTokenLimits[_llmModel]?.toDouble() ?? 32768),
              divisions: 50,
              onChanged: (value) {
                setState(() {
                  _maxTokens = value.round();
                });
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCreateButton() {
    return GradientButton(
      onPressed: _isLoading ? null : _createAgentFromForm,
      gradient: LinearGradient(
        colors: [
          Theme.of(context).colorScheme.primary,
          Theme.of(context).colorScheme.secondary,
        ],
      ),
      height: 56,
      child: _isLoading
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                color: Colors.white,
                strokeWidth: 2,
              ),
            )
          : const Text(
              'Create Agent',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Colors.white,
              ),
            ),
    );
  }
}
