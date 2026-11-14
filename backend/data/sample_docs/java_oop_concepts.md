# Object-Oriented Programming (OOP) Concepts in Java

Java is a class-based, object-oriented programming language designed around four primary core principles (pillars) of OOP:

## 1. Encapsulation
Encapsulation is the mechanism of wrapping data (variables) and code acting on the data (methods) together as a single unit. It restricts direct access to some of an object's components using private access modifiers, providing public getters and setters to protect internal state.

## 2. Inheritance
Inheritance allows a new class (subclass or child) to inherit properties and behaviors from an existing class (superclass or parent) using the `extends` keyword. It promotes code reusability and establishes an "IS-A" relationship.

## 3. Polymorphism
Polymorphism ("many forms") enables one interface or method name to perform different actions:
- **Compile-time Polymorphism (Method Overloading)**: Multiple methods within the same class have the same name but different parameter lists.
- **Runtime Polymorphism (Method Overriding)**: A subclass provides a specific implementation of a method already defined in its superclass using `@Override`.

## 4. Abstraction
Abstraction is the process of hiding internal implementation details and showing only essential features to the user. In Java, abstraction is achieved using:
- **Abstract Classes**: Declared with `abstract`, can contain both abstract and concrete methods.
- **Interfaces**: Contracts declared with `interface` keyword specifying what a class must do, implemented using `implements`.

