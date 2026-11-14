# FastAPI Routing and Path Operations

FastAPI provides intuitive routing capabilities using standard Python decorator syntax. Path operations define endpoints, HTTP methods, and URL parameters with automatic validation powered by Pydantic.

## Path Parameters and Validation
You can declare path parameters directly in the function signature using Python type hints. FastAPI automatically validates incoming path parameters against the declared types, returning detailed JSON error responses on type mismatches.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```
