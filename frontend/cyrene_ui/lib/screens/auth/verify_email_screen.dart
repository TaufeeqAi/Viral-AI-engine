import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';
import 'package:cyrene_ui/config/app_config.dart';

class VerifyEmailScreen extends StatelessWidget {
  final String email;
  const VerifyEmailScreen({super.key, required this.email});

  Future<void> _resendEmail(BuildContext context) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.fastApiAuthUrl}/resend-verification'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email}),
      );

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Verification email sent")),
        );
      } else {
        throw Exception('Failed to resend');
      }
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text("Error: $e")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Verify Your Email")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(
              "A verification link was sent to $email. Please check your inbox.",
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () => _resendEmail(context),
              child: const Text("Resend Verification Email"),
            ),
          ],
        ),
      ),
    );
  }
}
