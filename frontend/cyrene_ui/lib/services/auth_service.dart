// services/auth_service.dart
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'dart:async';
import '../config/app_config.dart';
import '../models/user.dart'; // Assuming this model has an 'id' field
import '../models/auth_response.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

class AuthService with ChangeNotifier {
  String? _accessToken;
  String? _refreshToken;
  User? _user;
  bool _isLoading = true;
  Timer? _tokenRefreshTimer;

  bool get isAuthenticated {
    final authenticated = _accessToken != null && _user != null;
    debugPrint(
      '🔍 [AUTH] isAuthenticated check: $authenticated (token: ${_accessToken != null}, user: ${_user != null})',
    );
    return authenticated;
  }

  String? get accessToken {
    debugPrint(
      '🔍 [AUTH] Getting accessToken: ${_accessToken != null ? "EXISTS" : "NULL"}',
    );
    return _accessToken;
  }

  String? get refreshToken {
    debugPrint(
      '🔍 [AUTH] Getting refreshToken: ${_refreshToken != null ? "EXISTS" : "NULL"}',
    );
    return _refreshToken;
  }

  String? get token {
    debugPrint(
      '🔍 [AUTH] Getting token (alias for accessToken): ${_accessToken != null ? "EXISTS" : "NULL"}',
    );
    return _accessToken;
  }

  User? get user {
    debugPrint(
      '🔍 [AUTH] Getting user: ${_user != null ? _user!.username : "NULL"}',
    );
    return _user;
  }

  // NEW: Getter to expose the user's ID from the _user object
  String? get userId {
    debugPrint(
      '🔍 [AUTH] Getting userId: ${_user != null ? _user!.id : "NULL"}',
    );
    return _user?.id;
  }

  bool get isLoading {
    debugPrint('🔍 [AUTH] isLoading: $_isLoading');
    return _isLoading;
  }

  AuthService() {
    debugPrint('🚀 [AUTH] AuthService constructor called');
    _loadTokens();
  }

  @override
  void dispose() {
    debugPrint('💀 [AUTH] AuthService disposing');
    _tokenRefreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadTokens() async {
    debugPrint('📂 [AUTH] Starting _loadTokens');
    _isLoading = true;
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      _accessToken = prefs.getString('access_token');
      _refreshToken = prefs.getString('refresh_token');

      debugPrint('📂 [AUTH] Loaded from SharedPreferences:');
      debugPrint(
        '   - Access Token: ${_accessToken != null ? "EXISTS (${_accessToken!.length} chars)" : "NULL"}',
      );
      debugPrint(
        '   - Refresh Token: ${_refreshToken != null ? "EXISTS (${_refreshToken!.length} chars)" : "NULL"}',
      );

      if (_accessToken != null && _refreshToken != null) {
        debugPrint('📂 [AUTH] Both tokens exist, validating...');
        await _validateAndRefreshToken();
      } else {
        debugPrint('📂 [AUTH] Missing tokens, user needs to login');
      }
    } catch (e) {
      debugPrint('❌ [AUTH] Error loading tokens: $e');
      debugPrint('📂 [AUTH] Clearing tokens due to error');
      await _clearTokens();
    } finally {
      _isLoading = false;
      debugPrint('📂 [AUTH] _loadTokens completed, isLoading: $_isLoading');
      notifyListeners();
    }
  }

  Future<void> _validateAndRefreshToken() async {
    debugPrint('✅ [AUTH] Starting token validation');

    try {
      final url = '${AppConfig.fastApiAuthUrl}/me';
      debugPrint('✅ [AUTH] Making request to: $url');
      debugPrint('✅ [AUTH] Using token: ${_accessToken?.substring(0, 20)}...');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Authorization': 'Bearer $_accessToken'},
      );

      debugPrint('✅ [AUTH] Validation response status: ${response.statusCode}');
      debugPrint('✅ [AUTH] Validation response body: ${response.body}');

      if (response.statusCode == 200) {
        debugPrint('✅ [AUTH] Token is valid, parsing user data');
        final userData = jsonDecode(response.body);
        debugPrint('✅ [AUTH] User data received: $userData');
        _user = User.fromJson(userData);
        debugPrint('✅ [AUTH] User object created: ${_user?.username}');
        _scheduleTokenRefresh();
      } else if (response.statusCode == 401 && _refreshToken != null) {
        debugPrint('✅ [AUTH] Token expired (401), attempting refresh');
        await _refreshAccessToken();
      } else {
        debugPrint('✅ [AUTH] Token validation failed, logging out');
        await logout();
      }
    } catch (e) {
      debugPrint('❌ [AUTH] Token validation failed with error: $e');
      if (_refreshToken != null) {
        debugPrint('✅ [AUTH] Attempting token refresh after validation error');
        await _refreshAccessToken();
      } else {
        debugPrint('✅ [AUTH] No refresh token available, logging out');
        await logout();
      }
    }
  }

  Future<void> _refreshAccessToken() async {
    debugPrint('🔄 [AUTH] Starting token refresh');

    try {
      final url = '${AppConfig.fastApiAuthUrl}/refresh';
      debugPrint('🔄 [AUTH] Refresh URL: $url');
      debugPrint(
        '🔄 [AUTH] Using refresh token: ${_refreshToken?.substring(0, 20)}...',
      );

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': _refreshToken}),
      );

      debugPrint('🔄 [AUTH] Refresh response status: ${response.statusCode}');
      debugPrint('🔄 [AUTH] Refresh response body: ${response.body}');

      if (response.statusCode == 200) {
        debugPrint('🔄 [AUTH] Token refresh successful');
        final authResponse = AuthResponse.fromJson(jsonDecode(response.body));
        _accessToken = authResponse.accessToken;
        _refreshToken = authResponse.refreshToken;

        debugPrint('🔄 [AUTH] New tokens received:');
        debugPrint('   - Access Token: ${_accessToken?.substring(0, 50)}...');
        debugPrint('   - Refresh Token: ${_refreshToken?.substring(0, 20)}...');

        await _saveTokens();
        await _getUserInfo();
        _scheduleTokenRefresh();
      } else {
        debugPrint('❌ [AUTH] Token refresh failed, logging out');
        await logout();
      }
    } catch (e) {
      debugPrint('❌ [AUTH] Token refresh failed with error: $e');
      await logout();
    }
  }

  Future<void> _getUserInfo() async {
    debugPrint('👤 [AUTH] Getting user info');

    try {
      final url = '${AppConfig.fastApiAuthUrl}/me';
      debugPrint('👤 [AUTH] User info URL: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Authorization': 'Bearer $_accessToken'},
      );

      debugPrint('👤 [AUTH] User info response status: ${response.statusCode}');
      debugPrint('👤 [AUTH] User info response body: ${response.body}');

      if (response.statusCode == 200) {
        final userData = jsonDecode(response.body);
        _user = User.fromJson(userData);
        debugPrint('👤 [AUTH] User info updated: ${_user?.username}');
      } else {
        debugPrint('❌ [AUTH] Failed to get user info');
        throw Exception('Failed to get user info');
      }
    } catch (e) {
      debugPrint('❌ [AUTH] Failed to get user info: $e');
      rethrow;
    }
  }

  void _scheduleTokenRefresh() {
    debugPrint('⏰ [AUTH] Scheduling token refresh');
    _tokenRefreshTimer?.cancel();

    // Refresh token 5 minutes before expiry (25 minutes for 30-minute tokens)
    _tokenRefreshTimer = Timer(const Duration(minutes: 25), () {
      debugPrint('⏰ [AUTH] Timer triggered, refreshing token');
      _refreshAccessToken();
    });
    debugPrint('⏰ [AUTH] Token refresh scheduled for 25 minutes from now');
  }

  Future<void> _saveTokens() async {
    debugPrint('💾 [AUTH] Saving tokens to SharedPreferences');

    final prefs = await SharedPreferences.getInstance();
    if (_accessToken != null) {
      await prefs.setString('access_token', _accessToken!);
      debugPrint('💾 [AUTH] Access token saved');
    }
    if (_refreshToken != null) {
      await prefs.setString('refresh_token', _refreshToken!);
      debugPrint('💾 [AUTH] Refresh token saved');
    }
    debugPrint('💾 [AUTH] Tokens saved successfully');
  }

  Future<void> _clearTokens() async {
    debugPrint('🗑️ [AUTH] Clearing all tokens and user data');

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
    _accessToken = null;
    _refreshToken = null;
    _user = null;
    _tokenRefreshTimer?.cancel();

    debugPrint('🗑️ [AUTH] All tokens and user data cleared');
  }

  Future<void> register({
    required String username,
    required String email,
    required String password,
    String? fullName,
  }) async {
    debugPrint('📝 [AUTH] Starting registration for user: $username');

    _isLoading = true;
    notifyListeners();

    try {
      final url = '${AppConfig.fastApiAuthUrl}/register';
      debugPrint('📝 [AUTH] Registration URL: $url');

      final requestBody = {
        'username': username,
        'email': email,
        'password': password,
        'full_name': fullName,
      };
      final safeLogBody = Map<String, dynamic>.from(requestBody)
        ..remove('password');
      debugPrint('📝 [AUTH] Registration request body: $safeLogBody');
      // Don't log password

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      );

      debugPrint(
        '📝 [AUTH] Registration response status: ${response.statusCode}',
      );
      debugPrint('📝 [AUTH] Registration response body: ${response.body}');

      if (response.statusCode == 201) {
        debugPrint('📝 [AUTH] Registration successful, attempting login');
        await login(username, password);
      } else {
        final errorData = jsonDecode(response.body);
        debugPrint('❌ [AUTH] Registration failed: ${errorData['detail']}');
        throw Exception(errorData['detail'] ?? 'Registration failed');
      }
    } catch (e) {
      debugPrint('❌ [AUTH] Registration error: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
      debugPrint('📝 [AUTH] Registration process completed');
    }
  }

  Future<void> login(String username, String password) async {
    debugPrint('🔐 [AUTH] Starting login for user: $username');

    _isLoading = true;
    notifyListeners();

    try {
      final url = '${AppConfig.fastApiAuthUrl}/login';
      debugPrint('🔐 [AUTH] Login URL: $url');

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: {'username': username, 'password': password},
      );

      debugPrint('🔐 [AUTH] Login response status: ${response.statusCode}');
      debugPrint('🔐 [AUTH] Login response body: ${response.body}');

      if (response.statusCode == 200) {
        debugPrint('🔐 [AUTH] Login successful, parsing tokens');
        final authResponse = AuthResponse.fromJson(jsonDecode(response.body));
        _accessToken = authResponse.accessToken;
        _refreshToken = authResponse.refreshToken;

        debugPrint('🔐 [AUTH] Tokens received:');
        debugPrint('   - Access Token: ${_accessToken?.substring(0, 50)}...');
        debugPrint('   - Refresh Token: ${_refreshToken?.substring(0, 20)}...');

        // Decode and log JWT payload
        final decoded = JwtDecoder.decode(_accessToken!);
        debugPrint('📦 [AUTH] Decoded Token Payload: $decoded');

        await _saveTokens();
        await _getUserInfo(); // This will populate _user and thus userId
        _scheduleTokenRefresh();

        debugPrint('🔐 [AUTH] Login process completed successfully');
      } else {
        final errorData = jsonDecode(response.body);
        debugPrint('❌ [AUTH] Login failed: ${errorData['detail']}');
        throw Exception(errorData['detail'] ?? 'Login failed');
      }
    } catch (e) {
      debugPrint('❌ [AUTH] Login error: $e');
      final error = e.toString();
      _isLoading = false;
      notifyListeners();
      if (error.contains('Email not verified')) {
        // Let UI know user needs to verify email
        throw Exception('email_not_verified');
      }
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
      debugPrint('🔐 [AUTH] Login process completed');
    }
  }

  Future<void> logout() async {
    debugPrint('🚪 [AUTH] Starting logout process');

    try {
      if (_accessToken != null) {
        debugPrint('🚪 [AUTH] Calling logout endpoint');
        final url = '${AppConfig.fastApiAuthUrl}/logout';

        final response = await http.post(
          Uri.parse(url),
          headers: {'Authorization': 'Bearer $_accessToken'},
        );

        debugPrint('🚪 [AUTH] Logout response status: ${response.statusCode}');
        debugPrint('🚪 [AUTH] Logout response body: ${response.body}');
      } else {
        debugPrint('🚪 [AUTH] No access token, skipping logout API call');
      }
    } catch (e) {
      debugPrint('❌ [AUTH] Logout API call failed: $e');
    } finally {
      await _clearTokens();
      notifyListeners();
      debugPrint('🚪 [AUTH] Logout process completed');
    }
  }

  Future<void> updateProfile({
    String? username,
    String? email,
    String? fullName,
    String? password,
  }) async {
    debugPrint('✏️ [AUTH] Starting profile update');

    if (_accessToken == null) {
      debugPrint('❌ [AUTH] Update profile failed: Not authenticated');
      throw Exception('Not authenticated');
    }

    _isLoading = true;
    notifyListeners();

    try {
      final Map<String, dynamic> updateData = {};
      if (username != null) updateData['username'] = username;
      if (email != null) updateData['email'] = email;
      if (fullName != null) updateData['full_name'] = fullName;
      if (password != null) updateData['password'] = password;

      debugPrint(
        '✏️ [AUTH] Update data: ${updateData..remove('password')}',
      ); // Don't log password

      final url = '${AppConfig.fastApiAuthUrl}/me';
      final response = await http.put(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_accessToken',
        },
        body: jsonEncode(updateData),
      );

      debugPrint('✏️ [AUTH] Update response status: ${response.statusCode}');
      debugPrint('✏️ [AUTH] Update response body: ${response.body}');

      if (response.statusCode == 200) {
        final userData = jsonDecode(response.body);
        _user = User.fromJson(userData);
        debugPrint(
          '✏️ [AUTH] Profile updated successfully: ${_user?.username}',
        );
      } else {
        final errorData = jsonDecode(response.body);
        debugPrint('❌ [AUTH] Profile update failed: ${errorData['detail']}');
        throw Exception(errorData['detail'] ?? 'Update failed');
      }
    } catch (e) {
      debugPrint('❌ [AUTH] Profile update error: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
      debugPrint('✏️ [AUTH] Profile update process completed');
    }
  }

  Future<Map<String, String>> getAuthHeaders() async {
    debugPrint('🔑 [AUTH] Getting auth headers');

    if (_accessToken == null) {
      debugPrint('❌ [AUTH] Cannot get auth headers: Not authenticated');
      throw Exception('Not authenticated');
    }

    final headers = {'Authorization': 'Bearer $_accessToken'};
    debugPrint(
      '🔑 [AUTH] Auth headers created with token: ${_accessToken?.substring(0, 20)}...',
    );
    return headers;
  }

  Future<bool> validateToken() async {
    debugPrint('🔍 [AUTH] Validating token');

    if (_accessToken == null) {
      debugPrint('🔍 [AUTH] No token to validate');
      return false;
    }

    try {
      final url = '${AppConfig.fastApiAuthUrl}/validate_token';
      final response = await http.get(
        Uri.parse(url),
        headers: {'Authorization': 'Bearer $_accessToken'},
      );

      final isValid = response.statusCode == 200;
      debugPrint(
        '🔍 [AUTH] Token validation result: $isValid (status: ${response.statusCode})',
      );
      return isValid;
    } catch (e) {
      debugPrint('❌ [AUTH] Token validation error: $e');
      return false;
    }
  }
}
