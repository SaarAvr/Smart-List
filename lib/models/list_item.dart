import 'package:cloud_firestore/cloud_firestore.dart';

class ListItem {
  final String id;
  final String name;
  final String listId;
  final String addedBy;
  final DateTime addedAt;
  final String? purchasedBy;
  final DateTime? purchasedAt;
  final Map<String, dynamic>? priceData; // {storeId: price}

  ListItem({
    required this.id,
    required this.name,
    required this.listId,
    required this.addedBy,
    required this.addedAt,
    this.purchasedBy,
    this.purchasedAt,
    this.priceData,
  });

  factory ListItem.fromMap(Map<String, dynamic> map, String id) {
    return ListItem(
      id: id,
      name: map['name'] ?? '',
      listId: map['listId'] ?? '',
      addedBy: map['addedBy'] ?? '',
      addedAt: (map['addedAt'] as Timestamp).toDate(),
      purchasedBy: map['purchasedBy'],
      purchasedAt: map['purchasedAt'] != null 
          ? (map['purchasedAt'] as Timestamp).toDate() 
          : null,
      priceData: map['priceData'],
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'name': name,
      'listId': listId,
      'addedBy': addedBy,
      'addedAt': addedAt,
      'purchasedBy': purchasedBy,
      'purchasedAt': purchasedAt,
      'priceData': priceData,
    };
  }

  bool get isPurchased => purchasedBy != null;

  ListItem copyWith({
    String? name,
    String? purchasedBy,
    DateTime? purchasedAt,
    Map<String, dynamic>? priceData,
  }) {
    return ListItem(
      id: id,
      name: name ?? this.name,
      listId: listId,
      addedBy: addedBy,
      addedAt: addedAt,
      purchasedBy: purchasedBy ?? this.purchasedBy,
      purchasedAt: purchasedAt ?? this.purchasedAt,
      priceData: priceData ?? this.priceData,
    );
  }
} 