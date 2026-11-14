# Pydantic v2 Models and Validation

Pydantic v2 is the data validation core of modern Python frameworks like FastAPI and LangGraph. It utilizes Rust-powered core validation logic to enforce strict type safety, automatic data coercion, and custom field validators.

## Base Model Configuration
Models inherit from `BaseModel` and utilize `Field` for detailed constraints, descriptions, and default values. ConfigDict allows fine-tuning model behaviors such as extra attribute handling and immutability.
