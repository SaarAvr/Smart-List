import 'package:flutter/material.dart';
import '../models/shopping_list.dart';
import '../services/firestore_service.dart';
import 'user_settings_screen.dart';
import 'list_detail_screen.dart';

class ListsScreen extends StatefulWidget {
  final String userId;

  const ListsScreen({super.key, required this.userId});

  @override
  State<ListsScreen> createState() => _ListsScreenState();
}

class _ListsScreenState extends State<ListsScreen> {
  final FirestoreService _firestoreService = FirestoreService();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Shopping Lists'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => UserSettingsScreen(userId: widget.userId),
                ),
              );
            },
          ),
        ],
      ),
      body: StreamBuilder<List<ShoppingList>>(
        stream: _firestoreService.getUserLists(widget.userId),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Text('Error: ${snapshot.error}'),
            );
          }

          final lists = snapshot.data ?? [];

          if (lists.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.shopping_cart_outlined, size: 64, color: Colors.grey),
                  SizedBox(height: 16),
                  Text(
                    'No shopping lists yet',
                    style: TextStyle(fontSize: 18, color: Colors.grey),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Create your first list to get started!',
                    style: TextStyle(color: Colors.grey),
                  ),
                ],
              ),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: lists.length,
            itemBuilder: (context, index) {
              final list = lists[index];
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  leading: const Icon(Icons.shopping_cart),
                  title: Text(list.name),
                  subtitle: Text('${list.members.length} members'),
                  trailing: const Icon(Icons.arrow_forward_ios),
                  onTap: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ListDetailScreen(list: list),
                      ),
                    );
                  },
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateListDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }

  Future<void> _showCreateListDialog(BuildContext context) async {
    final _formKey = GlobalKey<FormState>();
    final _nameController = TextEditingController();
    bool loading = false;
    String? error;

    await showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Create New List'),
              content: Form(
                key: _formKey,
                child: TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(labelText: 'List Name'),
                  validator: (value) => (value == null || value.trim().isEmpty) ? 'Please enter a name' : null,
                ),
              ),
              actions: [
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: Text(error!, style: const TextStyle(color: Colors.red)),
                  ),
                TextButton(
                  onPressed: loading ? null : () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: loading
                      ? null
                      : () async {
                          if (!_formKey.currentState!.validate()) return;
                          setState(() => loading = true);
                          try {
                            final userId = widget.userId;
                            final list = ShoppingList(
                              id: '',
                              name: _nameController.text.trim(),
                              createdBy: userId,
                              members: [userId],
                              createdAt: DateTime.now(),
                              lastModified: null,
                            );
                            await FirestoreService().createShoppingList(list);
                            Navigator.of(context).pop();
                          } catch (e) {
                            setState(() {
                              error = 'Failed to create list: $e';
                              loading = false;
                            });
                          }
                        },
                  child: loading ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Create'),
                ),
              ],
            );
          },
        );
      },
    );
  }
} 