import 'package:flutter/material.dart';
import '../models/shopping_list.dart';
import '../models/list_item.dart';
import '../services/firestore_service.dart';
import 'package:http/http.dart' as http;
import 'package:html/parser.dart' as html_parser;
import 'package:html/dom.dart' as dom;
import 'dart:convert';

class ListDetailScreen extends StatefulWidget {
  final ShoppingList list;
  const ListDetailScreen({super.key, required this.list});

  @override
  State<ListDetailScreen> createState() => _ListDetailScreenState();
}

class _ListDetailScreenState extends State<ListDetailScreen> {
  final FirestoreService _firestoreService = FirestoreService();

  Future<void> _showAddItemDialog() async {
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
              title: const Text('Add Item'),
              content: Form(
                key: _formKey,
                child: TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(labelText: 'Item Name'),
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
                            final item = ListItem(
                              id: '',
                              name: _nameController.text.trim(),
                              listId: widget.list.id,
                              addedBy: widget.list.createdBy,
                              addedAt: DateTime.now(),
                              purchasedBy: null,
                              purchasedAt: null,
                              priceData: null,
                            );
                            await _firestoreService.addItem(item);
                            Navigator.of(context).pop();
                          } catch (e) {
                            setState(() {
                              error = 'Failed to add item: $e';
                              loading = false;
                            });
                          }
                        },
                  child: loading ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Add'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _showMembersDialog() async {
    final _formKey = GlobalKey<FormState>();
    final _emailController = TextEditingController();
    bool loading = false;
    String? error;
    List<String> members = List.from(widget.list.members);
    List<String> memberNames = [];

    // Fetch user names for all member IDs
    try {
      final users = await Future.wait(members.map((id) => FirestoreService().getUser(id)));
      memberNames = users.map((u) => u?.name ?? u?.email ?? 'Unknown').toList();
    } catch (_) {
      memberNames = members;
    }

    await showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('List Members'),
              content: SizedBox(
                width: 300,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Current members:'),
                    const SizedBox(height: 8),
                    ...memberNames.map((name) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2.0),
                          child: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
                        )),
                    const Divider(height: 24),
                    const Text('Add new member by email:'),
                    Form(
                      key: _formKey,
                      child: TextFormField(
                        controller: _emailController,
                        decoration: const InputDecoration(labelText: 'Email'),
                        validator: (value) => (value == null || value.trim().isEmpty) ? 'Enter email' : null,
                      ),
                    ),
                    if (error != null) ...[
                      const SizedBox(height: 8),
                      Text(error!, style: const TextStyle(color: Colors.red)),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: loading ? null : () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
                ElevatedButton(
                  onPressed: loading
                      ? null
                      : () async {
                          if (!_formKey.currentState!.validate()) return;
                          setState(() => loading = true);
                          try {
                            // Find user by email
                            final user = await FirestoreService().getUserByEmail(_emailController.text.trim());
                            if (user == null) {
                              setState(() {
                                error = 'No user found with that email.';
                                loading = false;
                              });
                              return;
                            }
                            if (members.contains(user.id)) {
                              setState(() {
                                error = 'User is already a member.';
                                loading = false;
                              });
                              return;
                            }
                            members.add(user.id);
                            final updatedList = widget.list.copyWith(members: members);
                            await FirestoreService().updateShoppingList(updatedList);
                            setState(() {
                              error = null;
                              loading = false;
                            });
                          } catch (e) {
                            setState(() {
                              error = 'Failed to add member: $e';
                              loading = false;
                            });
                          }
                        },
                  child: loading ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Add'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.list.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.group),
            tooltip: 'View/Add Members',
            onPressed: _showMembersDialog,
          ),
        ],
      ),
      body: StreamBuilder<List<ListItem>>(
        stream: _firestoreService.getListItems(widget.list.id),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final items = snapshot.data ?? [];
          if (items.isEmpty) {
            return const Center(child: Text('No items yet.'));
          }
          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  title: Text(item.name),
                  // TODO: Add more item details/actions
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          FloatingActionButton(
            heroTag: 'addItem',
            onPressed: _showAddItemDialog,
            child: const Icon(Icons.add),
            tooltip: 'Add Item',
          ),
          const SizedBox(width: 16),
          FloatingActionButton(
            heroTag: 'findCheapest',
            onPressed: _onFindCheapestPressed,
            child: const Icon(Icons.local_offer),
            tooltip: 'Find Cheapest Store',
          ),
        ],
      ),
    );
  }

  void _onFindCheapestPressed() async {
    const proxyUrl = 'http://192.168.126.5:5000/get-first-chain-branches';
    showDialog(
      context: context,
      builder: (context) => const AlertDialog(
        title: Text('Fetching...'),
        content: SizedBox(height: 80, child: Center(child: CircularProgressIndicator())),
      ),
      barrierDismissible: false,
    );

    try {
      final response = await http.get(Uri.parse(proxyUrl));
      if (response.statusCode != 200) {
        Navigator.of(context).pop();
        showDialog(
          context: context,
          builder: (context) => const AlertDialog(
            title: Text('Error'),
            content: Text('Failed to fetch branches from backend proxy.'),
          ),
        );
        return;
      }
      final json = jsonDecode(response.body);
      final branches = json['branches'] as Map<String, dynamic>? ?? {};
      // Sort branches by code (as int if possible)
      final sortedEntries = branches.entries.toList()
        ..sort((a, b) => int.tryParse(a.value.toString())?.compareTo(int.tryParse(b.value.toString()) ?? 0) ?? a.value.toString().compareTo(b.value.toString()));
      Navigator.of(context).pop();
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Branches (via Proxy)'),
          content: SizedBox(
            width: 300,
            height: 400,
            child: ListView(
              children: sortedEntries.map((entry) {
                return ListTile(
                  title: Text(entry.key),
                  subtitle: Text('Code: ${entry.value}'),
                );
              }).toList(),
            ),
          ),
        ),
      );
    } catch (e) {
      Navigator.of(context).pop();
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Error'),
          content: Text('Failed to fetch or parse from proxy: $e'),
        ),
      );
    }
  }
} 