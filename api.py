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

# Определяем, где запущено приложение
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
        # Демо-данные, если файла нет
        return [
            {"id": 1, "title": "Квартира на Патриарших", "price": 8900, "address": "Москва, Патриаршая, 12", "city": "Москва"},
            {"id": 2, "title": "Студия у моря", "price": 5200, "address": "Сочи, Приморская, 5", "city": "Сочи"},
            {"id": 3, "title": "Апартаменты Арбат", "price": 12500, "address": "Москва, Арбат, 8", "city": "Москва"},
        ]
    
    # Фильтрация по городу и цене
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
        # Локальный режим (Selenium)
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            import time
        except ImportError:
            return []
        
        city_map = {
            'москва': 'moskva', 'санкт-петербург': 'sankt-peterburg',
            'сочи': 'sochi', 'казань': 'kazan', 'екатеринбург': 'ekaterinburg',
            'томск': 'tomsk', 'новосибирск': 'novosibirsk', 'краснодар': 'krasnodar'
        }
        city_slug = city_map.get(city.lower(), city.lower().replace(' ', '_'))
        
        url = f"https://www.avito.ru/{city_slug}/kvartiry"
        if max_price:
            url += f"?price_to={max_price}"
        
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except:
            return []
        
        driver.get(url)
        time.sleep(5)
        
        items = driver.find_elements(By.CSS_SELECTOR, '[data-marker="item"]')
        apartments = []
        
        for item in items[:limit]:
            try:
                title = item.find_element(By.CSS_SELECTOR, 'h3').text.strip()
                price_elem = item.find_element(By.CSS_SELECTOR, '[data-marker="item-price"]')
                price_text = price_elem.text.strip()
                price = int(re.sub(r'[^\d]', '', price_text)) if price_text else 0
                
                try:
                    address = item.find_element(By.CSS_SELECTOR, '[data-marker="item-address"]').text.strip()
                except:
                    address = "Адрес не указан"
                
                link = item.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                
                apartments.append({
                    'id': abs(hash(link)) % 1000000,
                    'title': title,
                    'price': price,
                    'price_raw': price_text,
                    'address': address,
                    'link': link,
                    'city': city
                })
            except:
                continue
        
        return apartments


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "demo" if IS_RENDER else "selenium"}


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
