# FastAPI Dependency Injection System

FastAPI features a robust and powerful Dependency Injection system. It allows developers to build reusable logic components, database sessions, authentication checks, and shared configurations that can be injected into path operation functions effortlessly.

## Using Depends
Dependencies are declared using the `Depends` class. FastAPI evaluates dependency callables, resolves their sub-dependencies recursively, and supplies the resulting values to the path operation function.
