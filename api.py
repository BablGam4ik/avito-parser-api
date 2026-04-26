import time
import json
import os
import re
from typing import Optional, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    city: str
    max_price: Optional[int] = None


def clean_price(price_str: str) -> int:
    """Очистка цены от символов и преобразование в число"""
    if price_str:
        cleaned = re.sub(r'[^\d]', '', str(price_str))
        return int(cleaned) if cleaned else 0
    return 0


def search_avito(city: str, max_price: Optional[int] = None, limit: int = 30) -> List[dict]:
    """Парсинг квартир на Авито через Selenium"""

    # Транслитерация города
    city_map = {
        'москва': 'moskva',
        'санкт-петербург': 'sankt-peterburg',
        'сочи': 'sochi',
        'казань': 'kazan',
        'екатеринбург': 'ekaterinburg',
        'томск': 'tomsk',
        'новосибирск': 'novosibirsk',
        'краснодар': 'krasnodar'
    }
    city_slug = city_map.get(city.lower(), city.lower().replace(' ', '_'))

    # Формируем URL
    url = f"https://www.avito.ru/{city_slug}/kvartiry"
    if max_price:
        url += f"?price_to={max_price}"

    print(f"🌐 URL: {url}")

    # Подключаемся к уже открытому браузеру
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ Подключение к браузеру успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("👉 Запустите браузер командой:")
        print(
            '   "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\chrome_profile_avito"')
        return []

    driver.get(url)
    time.sleep(5)

    # Пробуем разные селекторы для карточек
    items = []
    selectors = [
        '[data-marker="item"]',
        '.iva-item-root',
        '[class*="item"]',
        'div[data-marker*="item"]',
        '.item-view'
    ]

    for selector in selectors:
        try:
            found = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(found) > 0:
                items = found
                print(f"✅ Найдено {len(items)} карточек через селектор: {selector}")
                break
        except:
            continue

    if len(items) == 0:
        print("❌ Не удалось найти карточки ни одним селектором")
        return []

    apartments = []

    for idx, item in enumerate(items[:limit]):
        try:
            # === НАЗВАНИЕ (несколько попыток) ===
            title = "Квартира"
            title_selectors = [
                'h3',
                '[itemprop="name"]',
                '[data-marker*="title"]',
                '.title-root',
                'a[itemprop="url"]',
                'div[class*="title"]'
            ]
            for sel in title_selectors:
                try:
                    title_elem = item.find_element(By.CSS_SELECTOR, sel)
                    title_text = title_elem.text.strip()
                    if title_text and len(title_text) > 2:
                        title = title_text
                        break
                except:
                    continue

            # === ЦЕНА ===
            price = 0
            price_raw = "0"
            price_selectors = [
                '[data-marker="item-price"]',
                '[itemprop="price"]',
                'span[class*="price"]',
                'div[class*="price"]'
            ]
            for sel in price_selectors:
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, sel)
                    price_raw = price_elem.text.strip() or price_elem.get_attribute('content', '0')
                    price = clean_price(price_raw)
                    if price > 0:
                        break
                except:
                    continue

            # === АДРЕС ===
            address = "Адрес не указан"
            address_selectors = [
                '[data-marker="item-address"]',
                '[class*="address"]',
                'div[class*="geo"]'
            ]
            for sel in address_selectors:
                try:
                    address_elem = item.find_element(By.CSS_SELECTOR, sel)
                    address_text = address_elem.text.strip()
                    if address_text:
                        address = address_text
                        break
                except:
                    continue

            # === ССЫЛКА ===
            link = ""
            try:
                link_elem = item.find_element(By.CSS_SELECTOR, 'a')
                link = link_elem.get_attribute('href')
                if not link:
                    link = ""
            except:
                pass

            # === МЕТРО (если есть) ===
            metro = ""
            try:
                metro_elem = item.find_element(By.CSS_SELECTOR, '[data-marker="item-metro"]')
                metro = metro_elem.text.strip()
            except:
                pass

            # Добавляем только если есть цена и название
            if price > 0 or title != "Квартира":
                apartments.append({
                    'id': abs(hash(link)) % 1000000 if link else idx,
                    'title': title,
                    'price': price,
                    'price_raw': price_raw,
                    'address': address,
                    'metro': metro,
                    'link': link,
                    'city': city
                })
                print(f"  {len(apartments)}. {title[:45]} - {price:,} ₽".replace(',', ' '))

        except Exception as e:
            print(f"  ⚠️ Ошибка в карточке {idx}: {str(e)[:50]}")
            continue

    print(f"🎉 Итого собрано: {len(apartments)} квартир")
    return apartments


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/search")
async def search(request: SearchRequest):
    print(f"\n📥 Запрос: город={request.city}, макс.цена={request.max_price}")
    try:
        apartments = search_avito(
            city=request.city,
            max_price=request.max_price,
            limit=30
        )
        return {
            "success": True,
            "count": len(apartments),
            "apartments": apartments
        }
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {
            "success": False,
            "message": str(e),
            "apartments": []
        }


if __name__ == "__main__":
    import uvicorn

    print("""
╔═══════════════════════════════════════════════════════════════╗
║              🚀 АВИТО ПАРСЕР API - ЗАПУСК                      ║
╠═══════════════════════════════════════════════════════════════╣
║  Перед запуском убедитесь, что открыт браузер:               ║
║  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"   ║
║     --remote-debugging-port=9222                             ║
║     --user-data-dir="C:\\chrome_profile_avito"                ║
╠═══════════════════════════════════════════════════════════════╣
║  API доступен по адресу: http://localhost:8000               ║
║  POST /search - поиск квартир                                ║
║  GET  /health - проверка статуса                             ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)