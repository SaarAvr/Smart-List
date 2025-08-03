import 'package:cloud_firestore/cloud_firestore.dart';

class ShoppingList {
  final String id;
  final String name;
  final String createdBy;
  final List<String> members;
  final DateTime createdAt;
  final DateTime? lastModified;

  ShoppingList({
    required this.id,
    required this.name,
    required this.createdBy,
    required this.members,
    required this.createdAt,
    this.lastModified,
  });

  factory ShoppingList.fromMap(Map<String, dynamic> map, String id) {
    return ShoppingList(
      id: id,
      name: map['name'] ?? '',
      createdBy: map['createdBy'] ?? '',
      members: List<String>.from(map['members'] ?? []),
      createdAt: (map['createdAt'] as Timestamp).toDate(),
      lastModified: map['lastModified'] != null 
          ? (map['lastModified'] as Timestamp).toDate() 
          : null,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'name': name,
      'createdBy': createdBy,
      'members': members,
      'createdAt': createdAt,
      'lastModified': lastModified,
    };
  }

  ShoppingList copyWith({
    String? name,
    List<String>? members,
    DateTime? lastModified,
  }) {
    return ShoppingList(
      id: id,
      name: name ?? this.name,
      createdBy: createdBy,
      members: members ?? this.members,
      createdAt: createdAt,
      lastModified: lastModified ?? this.lastModified,
    );
  }
} 