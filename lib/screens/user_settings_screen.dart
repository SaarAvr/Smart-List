import 'package:flutter/material.dart';
import '../services/firestore_service.dart';
import '../models/user.dart' as app_user;
import '../services/auth_service.dart';
import '../screens/sign_in_screen.dart';

class UserSettingsScreen extends StatelessWidget {
  final String userId;
  const UserSettingsScreen({super.key, required this.userId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('User Settings')),
      body: FutureBuilder<app_user.User?>(
        future: FirestoreService().getUser(userId),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData || snapshot.data == null) {
            return const Center(child: Text('User not found.'));
          }
          final user = snapshot.data!;
          return Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Email: ${user.email}', style: const TextStyle(fontSize: 18)),
                const SizedBox(height: 16),
                Text('Name: ${user.name}', style: const TextStyle(fontSize: 18)),
                // Add more fields here (location, etc.)
                const SizedBox(height: 32),
                ElevatedButton.icon(
                  icon: const Icon(Icons.logout),
                  label: const Text('Log out'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () async {
                    await AuthService().signOut();
                    if (context.mounted) {
                      Navigator.of(context).pushAndRemoveUntil(
                        MaterialPageRoute(builder: (_) => const SignInScreen()),
                        (route) => false,
                      );
                    }
                  },
                ),
              ],
            ),
          );
        },
      ),
    );
  }
} 