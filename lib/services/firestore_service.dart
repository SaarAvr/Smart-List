import 'package:cloud_firestore/cloud_firestore.dart';
import '../models/user.dart';
import '../models/shopping_list.dart';
import '../models/list_item.dart';

class FirestoreService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  // User operations
  Future<void> createUser(User user) async {
    await _firestore.collection('users').doc(user.id).set(user.toMap());
  }

  Future<User?> getUser(String userId) async {
    final doc = await _firestore.collection('users').doc(userId).get();
    if (doc.exists) {
      return User.fromMap(doc.data()!, doc.id);
    }
    return null;
  }

  Future<User?> getUserByEmail(String email) async {
    final query = await _firestore.collection('users').where('email', isEqualTo: email).limit(1).get();
    if (query.docs.isNotEmpty) {
      final doc = query.docs.first;
      return User.fromMap(doc.data(), doc.id);
    }
    return null;
  }

  Future<void> updateUser(User user) async {
    await _firestore.collection('users').doc(user.id).update(user.toMap());
  }

  // Shopping list operations
  Future<String> createShoppingList(ShoppingList list) async {
    final docRef = await _firestore.collection('shopping_lists').add(list.toMap());
    return docRef.id;
  }

  Stream<List<ShoppingList>> getUserLists(String userId) {
    return _firestore
        .collection('shopping_lists')
        .where('members', arrayContains: userId)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => ShoppingList.fromMap(doc.data(), doc.id))
            .toList());
  }

  Future<ShoppingList?> getShoppingList(String listId) async {
    final doc = await _firestore.collection('shopping_lists').doc(listId).get();
    if (doc.exists) {
      return ShoppingList.fromMap(doc.data()!, doc.id);
    }
    return null;
  }

  Future<void> updateShoppingList(ShoppingList list) async {
    await _firestore.collection('shopping_lists').doc(list.id).update(list.toMap());
  }

  Future<void> deleteShoppingList(String listId) async {
    await _firestore.collection('shopping_lists').doc(listId).delete();
  }

  // List item operations
  Future<String> addItem(ListItem item) async {
    final docRef = await _firestore.collection('items').add(item.toMap());
    return docRef.id;
  }

  Stream<List<ListItem>> getListItems(String listId) {
    return _firestore
        .collection('items')
        .where('listId', isEqualTo: listId)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => ListItem.fromMap(doc.data(), doc.id))
            .toList());
  }

  Future<void> updateItem(ListItem item) async {
    await _firestore.collection('items').doc(item.id).update(item.toMap());
  }

  Future<void> deleteItem(String itemId) async {
    await _firestore.collection('items').doc(itemId).delete();
  }
} 