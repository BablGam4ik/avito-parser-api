import json
import os
import re
from typing import Optional, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

IS_RENDER = os.environ.get('RENDER') == 'true'

class SearchRequest(BaseModel):
    city: str
    max_price: Optional[int] = None


def load_from_json(city: str, max_price: Optional[int] = None, limit: int = 30) -> List[dict]:
    """Загрузка квартир из JSON-файла (для Render)"""
    try:
        with open('avito_apartments.json', 'r', encoding='utf-8') as f:
            all_apartments = json.load(f)
    except FileNotFoundError:
        return [
            {"id": 1, "title": "Квартира на Патриарших", "price": 8900, "address": "Москва, Патриаршая, 12", "city": "Москва"},
            {"id": 2, "title": "Студия у моря", "price": 5200, "address": "Сочи, Приморская, 5", "city": "Сочи"},
            {"id": 3, "title": "Апартаменты Арбат", "price": 12500, "address": "Москва, Арбат, 8", "city": "Москва"},
        ]
    
    filtered = []
    for apt in all_apartments:
        city_match = city.lower() in apt.get('city', '').lower() or city.lower() in apt.get('address', '').lower()
        price_match = max_price is None or apt.get('price', 0) <= max_price
        if city_match and price_match:
            filtered.append(apt)
    
    return filtered[:limit]


def search_avito(city: str, max_price: Optional[int] = None, limit: int = 30) -> List[dict]:
    """Автоматический выбор режима: на сервере — JSON, локально — Selenium"""
    if IS_RENDER:
        print(f"☁️  Render режим (JSON)")
        return load_from_json(city, max_price, limit)
    else:
        return []


@app.get("/")
async def root():
    return {"status": "ok", "message": "Avito Parser API", "endpoints": {"/health": "GET", "/search": "POST"}}


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "demo" if IS_RENDER else "local"}


@app.post("/search")
async def search(request: SearchRequest):
    print(f"\n📥 Запрос: город={request.city}, макс.цена={request.max_price}")
    apartments = search_avito(request.city, request.max_price, limit=30)
    return {
        "success": True,
        "count": len(apartments),
        "apartments": apartments
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
