from fastapi import APIRouter

router = APIRouter()


@router.get("/items")
def list_items():
    # Dispatched by the framework on request — never called directly in source.
    return []
