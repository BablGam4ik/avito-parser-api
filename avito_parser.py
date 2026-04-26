import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Настройки для подключения к вашему браузеру ---
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")


def clean_price(price_str):
    if price_str:
        cleaned = re.sub(r'[^\d]', '', price_str)
        return int(cleaned) if cleaned else 0
    return 0


print("🔄 Подключение к вашему браузеру Chrome...")
driver = webdriver.Chrome(options=chrome_options)
print("✅ Успешное подключение! Начинаем парсинг...")

# Открываем страницу
url = "https://www.avito.ru/moskva/kvartiry?p=1&price_to=150000"
driver.get(url)

# Ждём загрузки карточек (максимум 15 секунд)
wait = WebDriverWait(driver, 15)
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-marker="item"]')))

# Даём время на полную загрузку JavaScript
time.sleep(3)

# Ищем все карточки
items = driver.find_elements(By.CSS_SELECTOR, '[data-marker="item"]')
print(f"🔍 Найдено карточек: {len(items)}")

all_apartments = []

for idx, item in enumerate(items, 1):
    try:
        # ---- Способ 1: Через data-marker ----
        title = "Название не найдено"
        price_raw = "0"
        address = "Адрес не указан"
        link = ""

        # Название
        try:
            title_elem = item.find_element(By.CSS_SELECTOR, '[data-marker*="title"]')
            title = title_elem.text.strip()
        except:
            # Альтернативный поиск
            title_elem = item.find_element(By.CSS_SELECTOR, 'h3')
            title = title_elem.text.strip()

        # Цена
        try:
            price_elem = item.find_element(By.CSS_SELECTOR, '[data-marker*="price"]')
            price_raw = price_elem.text.strip()
        except:
            # Альтернативный поиск
            price_elem = item.find_element(By.CSS_SELECTOR, 'span[itemprop="price"]')
            price_raw = price_elem.get_attribute("content") or price_elem.text.strip()

        # Адрес
        try:
            address_elem = item.find_element(By.CSS_SELECTOR, '[data-marker*="address"]')
            address = address_elem.text.strip()
        except:
            pass

        # Ссылка
        try:
            link_elem = item.find_element(By.CSS_SELECTOR, 'a')
            link = link_elem.get_attribute('href')
        except:
            pass

        price = clean_price(price_raw)

        # Пропускаем явно невалидные объявления
        if price < 1000 and len(title) < 5:
            continue

        apartment = {
            'title': title,
            'price': price,
            'price_raw': price_raw,
            'address': address,
            'link': link
        }

        all_apartments.append(apartment)
        print(f"  {idx}. {title[:50]} - {price:,} ₽".replace(',', ' '))

    except Exception as e:
        print(f"  ❌ Ошибка в карточке {idx}: {e}")
        continue

print(f"\n🎉 Успешно собрано {len(all_apartments)} квартир!")

# Сохраняем результат
with open('avito_apartments.json', 'w', encoding='utf-8') as f:
    json.dump(all_apartments, f, ensure_ascii=False, indent=2)

print("💾 Результат сохранен в файл avito_apartments.json")
print("\n📋 Первые 3 квартиры для проверки:")
for i, apt in enumerate(all_apartments[:3], 1):
    print(f"{i}. {apt['title']} — {apt['price']:,} ₽".replace(',', ' '))
    print(f"   {apt['address']}")
    print(f"   {apt['link']}\n")