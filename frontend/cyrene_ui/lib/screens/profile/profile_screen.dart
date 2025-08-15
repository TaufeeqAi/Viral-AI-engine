// screens/profile_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../services/auth_service.dart';
import '../../../widgets/common/custom_text_field.dart';
import '../../../widgets/common/gradient_button.dart';
import '../../../widgets/common/error_message.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _fullNameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  bool _isEditing = false;
  bool _isPasswordVisible = false;
  bool _isConfirmPasswordVisible = false;
  String _errorMessage = '';
  String _successMessage = '';

  @override
  void initState() {
    super.initState();
    _loadUserData();
  }

  void _loadUserData() {
    final authService = Provider.of<AuthService>(context, listen: false);
    final user = authService.user;
    if (user != null) {
      _usernameController.text = user.username;
      _emailController.text = user.email;
      _fullNameController.text = user.fullName ?? '';
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _fullNameController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _updateProfile() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _errorMessage = '';
      _successMessage = '';
    });

    try {
      final authService = Provider.of<AuthService>(context, listen: false);
      final user = authService.user!;

      // Only send changed fields
      String? username = _usernameController.text.trim() != user.username
          ? _usernameController.text.trim()
          : null;
      String? email = _emailController.text.trim() != user.email
          ? _emailController.text.trim()
          : null;
      String? fullName =
          _fullNameController.text.trim() != (user.fullName ?? '')
          ? _fullNameController.text.trim()
          : null;
      String? password = _passwordController.text.isNotEmpty
          ? _passwordController.text
          : null;

      await authService.updateProfile(
        username: username,
        email: email,
        fullName: fullName,
        password: password,
      );

      setState(() {
        _isEditing = false;
        _successMessage = 'Profile updated successfully!';
        _passwordController.clear();
        _confirmPasswordController.clear();
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceAll('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          if (!_isEditing)
            IconButton(
              onPressed: () {
                setState(() {
                  _isEditing = true;
                  _errorMessage = '';
                  _successMessage = '';
                });
              },
              icon: const Icon(Icons.edit),
            ),
        ],
      ),
      body: Consumer<AuthService>(
        builder: (context, authService, child) {
          if (authService.user == null) {
            return const Center(child: Text('No user data available'));
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: _buildProfileForm(authService),
          );
        },
      ),
    );
  }

  Widget _buildProfileForm(AuthService authService) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment:
                CrossAxisAlignment.stretch, // Fixed: changed from crossAxisSize
            children: [
              _buildProfileHeader(authService.user!),
              const SizedBox(height: 32),
              _buildUsernameField(),
              const SizedBox(height: 16),
              _buildEmailField(),
              const SizedBox(height: 16),
              _buildFullNameField(),
              if (_isEditing) ...[
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 16),
                Text(
                  'Change Password (Optional)',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 16),
                _buildPasswordField(),
                const SizedBox(height: 16),
                _buildConfirmPasswordField(),
              ],
              const SizedBox(height: 24),
              if (_errorMessage.isNotEmpty) ...[
                ErrorMessage(message: _errorMessage),
                const SizedBox(height: 16),
              ],
              if (_successMessage.isNotEmpty) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.green.withValues(
                      alpha: 0.1,
                    ), // Fixed: using withValues instead of withOpacity
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: Colors.green.withValues(alpha: 0.3),
                    ), // Fixed: using withValues
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: Colors.green),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _successMessage,
                          style: TextStyle(color: Colors.green[700]),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (_isEditing) ...[
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () {
                          setState(() {
                            _isEditing = false;
                            _loadUserData();
                            _passwordController.clear();
                            _confirmPasswordController.clear();
                            _errorMessage = '';
                            _successMessage = '';
                          });
                        },
                        child: const Text('Cancel'),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: GradientButton(
                        onPressed: authService.isLoading
                            ? null
                            : _updateProfile,
                        gradient: LinearGradient(
                          colors: [
                            Theme.of(context).colorScheme.primary,
                            Theme.of(context).colorScheme.secondary,
                          ],
                        ),
                        child: authService.isLoading
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text(
                                'Save Changes',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProfileHeader(user) {
    return Column(
      children: [
        CircleAvatar(
          radius: 50,
          backgroundColor: Theme.of(context).colorScheme.primary.withValues(
            alpha: 0.2,
          ), // Fixed: using withValues
          child: Text(
            user.username.substring(0, 1).toUpperCase(),
            style: Theme.of(context).textTheme.headlineLarge?.copyWith(
              color: Theme.of(context).colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          user.fullName ?? user.username,
          style: Theme.of(
            context,
          ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text(
          user.email,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: Theme.of(context).colorScheme.onSurface.withValues(
              alpha: 0.6,
            ), // Fixed: using withValues
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: user.isActive ? Colors.green : Colors.red,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                user.isActive ? 'Active' : 'Inactive',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: user.isVerified ? Colors.blue : Colors.orange,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                user.isVerified ? 'Verified' : 'Unverified',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildUsernameField() {
    return CustomTextField(
      controller: _usernameController,
      label: 'Username',
      prefixIcon: Icons.person_outline,
      readOnly: !_isEditing, // Fixed: using readOnly instead of enabled
      validator: _isEditing
          ? (value) {
              if (value == null || value.isEmpty) {
                return 'Please enter a username';
              }
              if (value.length < 3) {
                return 'Username must be at least 3 characters';
              }
              return null;
            }
          : null,
    );
  }

  Widget _buildEmailField() {
    return CustomTextField(
      controller: _emailController,
      label: 'Email',
      prefixIcon: Icons.email_outlined,
      readOnly: !_isEditing, // Fixed: using readOnly instead of enabled
      keyboardType: TextInputType.emailAddress,
      validator: _isEditing
          ? (value) {
              if (value == null || value.isEmpty) {
                return 'Please enter your email';
              }
              if (!RegExp(
                r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$',
              ).hasMatch(value)) {
                return 'Please enter a valid email address';
              }
              return null;
            }
          : null,
    );
  }

  Widget _buildFullNameField() {
    return CustomTextField(
      controller: _fullNameController,
      label: 'Full Name',
      prefixIcon: Icons.badge_outlined,
      readOnly: !_isEditing, // Fixed: using readOnly instead of enabled
      validator: _isEditing
          ? (value) {
              if (value != null && value.isNotEmpty && value.length < 2) {
                return 'Full name must be at least 2 characters';
              }
              return null;
            }
          : null,
    );
  }

  Widget _buildPasswordField() {
    return CustomTextField(
      controller: _passwordController,
      label: 'New Password (Optional)',
      prefixIcon: Icons.lock_outline,
      obscureText: !_isPasswordVisible,
      suffixIcon: IconButton(
        icon: Icon(
          _isPasswordVisible ? Icons.visibility_off : Icons.visibility,
        ),
        onPressed: () {
          setState(() {
            _isPasswordVisible = !_isPasswordVisible;
          });
        },
      ),
      validator: (value) {
        if (value != null && value.isNotEmpty) {
          if (value.length < 8) {
            return 'Password must be at least 8 characters';
          }
          if (!RegExp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)').hasMatch(value)) {
            return 'Password must contain uppercase, lowercase, and number';
          }
        }
        return null;
      },
    );
  }

  Widget _buildConfirmPasswordField() {
    return CustomTextField(
      controller: _confirmPasswordController,
      label: 'Confirm New Password',
      prefixIcon: Icons.lock_outline,
      obscureText: !_isConfirmPasswordVisible,
      suffixIcon: IconButton(
        icon: Icon(
          _isConfirmPasswordVisible ? Icons.visibility_off : Icons.visibility,
        ),
        onPressed: () {
          setState(() {
            _isConfirmPasswordVisible = !_isConfirmPasswordVisible;
          });
        },
      ),
      validator: (value) {
        if (_passwordController.text.isNotEmpty) {
          if (value == null || value.isEmpty) {
            return 'Please confirm your new password';
          }
          if (value != _passwordController.text) {
            return 'Passwords do not match';
          }
        }
        return null;
      },
    );
  }
}
