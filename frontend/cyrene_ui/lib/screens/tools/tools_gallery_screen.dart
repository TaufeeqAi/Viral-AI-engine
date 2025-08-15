import 'package:cyrene_ui/models/tool_model.dart';
import 'package:cyrene_ui/services/api_service.dart';
import 'package:cyrene_ui/services/auth_service.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class ToolGalleryScreen extends StatelessWidget {
  const ToolGalleryScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final authService = Provider.of<AuthService>(context, listen: false);
    final apiService = ApiService(authService.token!);
    return FutureBuilder<List<Tool>>(
      future: apiService.getAllTools(),
      builder: (_, snap) {
        if (!snap.hasData) return Center(child: CircularProgressIndicator());
        final tools = snap.data!;
        return Scaffold(
          appBar: AppBar(title: const Text("Available Tools")),
          body: GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              childAspectRatio: 3 / 2,
            ),
            itemCount: tools.length,
            itemBuilder: (_, i) => Card(
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  children: [
                    Text(
                      tools[i].name,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Text(
                      tools[i].description ?? "No description",
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
