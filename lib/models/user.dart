import 'package:cloud_firestore/cloud_firestore.dart';

class User {
  final String id;
  final String name;
  final String email;
  final DateTime createdAt;
  final Map<String, dynamic>? location; // {lat: double, lng: double}

  User({
    required this.id,
    required this.name,
    required this.email,
    required this.createdAt,
    this.location,
  });

  factory User.fromMap(Map<String, dynamic> map, String id) {
    return User(
      id: id,
      name: map['name'] ?? '',
      email: map['email'] ?? '',
      createdAt: (map['createdAt'] as Timestamp).toDate(),
      location: map['location'],
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'name': name,
      'email': email,
      'createdAt': createdAt,
      'location': location,
    };
  }

  User copyWith({
    String? name,
    String? email,
    Map<String, dynamic>? location,
  }) {
    return User(
      id: id,
      name: name ?? this.name,
      email: email ?? this.email,
      createdAt: createdAt,
      location: location ?? this.location,
    );
  }
} 