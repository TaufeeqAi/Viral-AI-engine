import 'package:cyrene_ui/models/agent_config.dart';
import 'package:cyrene_ui/screens/agents/agent_detail_screen.dart';
import 'package:cyrene_ui/screens/agents/edit_agent_screen.dart';
import 'package:cyrene_ui/screens/auth/register_screen.dart';
import 'package:cyrene_ui/screens/auth/verify_email_screen.dart';
import 'package:cyrene_ui/screens/profile/profile_screen.dart';
import 'package:cyrene_ui/screens/settings/settings_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'config/app_config.dart';
import 'config/theme_config.dart';
import 'services/auth_service.dart';
import 'services/chat_service.dart'; // NEW: Import ChatService
import 'screens/splash_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/main_screen.dart';

void main() {
  runApp(const CyreneApp());
}

class CyreneApp extends StatelessWidget {
  const CyreneApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => AuthService(), // Provide AuthService once
        ),
        // Provide ChatService, which depends on AuthService
        ChangeNotifierProvider(
          create: (context) {
            final authService = context.read<AuthService>();
            return ChatService(authService.token ?? '');
          },
        ),
        // Add any other top-level providers here
      ],
      child: MaterialApp(
        title: AppConfig.appName,
        theme: ThemeConfig.lightTheme,
        darkTheme: ThemeConfig.darkTheme,
        themeMode: ThemeMode.system,
        debugShowCheckedModeBanner: false,
        // Set home directly to AppInitializer to handle auth state
        home: const AppInitializer(),
        onGenerateRoute: (settings) {
          // Keep onGenerateRoute for named routes beyond initial auth check
          switch (settings.name) {
            case Routes.login:
              return MaterialPageRoute(builder: (_) => const LoginScreen());
            case Routes.main:
              return MaterialPageRoute(builder: (_) => const MainScreen());
            case Routes.profile:
              return MaterialPageRoute(builder: (_) => const ProfileScreen());
            case Routes.settings:
              return MaterialPageRoute(builder: (_) => const SettingsScreen());
            case Routes.editAgent:
              final agentId = settings.arguments as String;
              return MaterialPageRoute(
                builder: (_) => EditAgentScreen(agentId: agentId),
              );
            case Routes.agentDetails:
              final agent = settings.arguments as AgentConfig;
              return MaterialPageRoute(
                builder: (_) => AgentDetailScreen(agent: agent),
              );
            case Routes.register:
              return MaterialPageRoute(
                builder: (_) => const RegisterationScreen(),
              );
            case Routes.verifyEmail:
              final email = settings.arguments as String;
              return MaterialPageRoute(
                builder: (_) => VerifyEmailScreen(email: email),
              );
            default:
              // Fallback for any unhandled routes
              return MaterialPageRoute(
                builder: (_) =>
                    const Scaffold(body: Center(child: Text('Page not found'))),
              );
          }
        },
      ),
    );
  }
}

class AppInitializer extends StatelessWidget {
  const AppInitializer({super.key});

  @override
  Widget build(BuildContext context) {
    // This Consumer correctly watches AuthService for changes
    return Consumer<AuthService>(
      builder: (context, auth, child) {
        if (auth.isLoading) {
          return const SplashScreen();
        }

        return auth.isAuthenticated ? const MainScreen() : const LoginScreen();
      },
    );
  }
}
