import time
import random
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from database import KrishaDB

def safe_get_text(element, default="не указано"):
    """Безопасно возвращает текст элемента или значение по умолчанию"""
    return element.get_text(strip=True) if element else default

def init_driver():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return uc.Chrome(options=options, use_subprocess=True)

def get_detailed_info(driver, url):
    """Извлекает только нужные характеристики со страницы объявления"""
    try:
        driver.get(url)
        time.sleep(random.uniform(3.0, 5.0))
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Словарь для сбора данных
        res = {
            'area': safe_get_text(soup.find('div', attrs={'data-name': 'live.square'}), 'не указано'),
            'year_built': safe_get_text(soup.find('div', attrs={'data-name': 'house.year'}), 'не указано'),
            'floor': safe_get_text(soup.find('div', attrs={'data-name': 'flat.floor'}), 'не указано')
        }

        # 1. Извлекаем Район (обычно в заголовке или хлебных крошках)
        # Ищем текст в заголовке адреса
        address_panel = soup.find('div', class_='offer__advert-title')
        if address_panel:
            title_text = address_panel.h1.get_text(strip=True) if address_panel.h1 else ""
            # Количество комнат часто в заголовке (например, "3-комнатная квартира")
            if "-комнатная" in title_text:
                res['rooms'] = title_text.split("-комнатная")[0].strip()


        # 2. Ищем характеристики в таблице (Площадь, Этаж, Год)
        info_items = soup.find_all('div', attrs={'data-name': ['live.square', 'house.year', 'flat.floor', 'flat.rooms']})
        for item in info_items:
            title = item.find('div', class_='offer__info-title').get_text(strip=True).lower()
            value = item.find('div', class_='offer__info-term').get_text(strip=True)

            if 'площадь' in title:
                res['area'] = value
            elif 'год постройки' in title:
                res['year_built'] = value
            elif 'этаж' in title:
                res['floor'] = value
            elif 'количество комнат' in title and res['rooms'] == 'не указано':
                res['rooms'] = value

        return res
    except Exception as e:
        print(f"Ошибка на странице {url}: {e}")
        return None

if __name__ == "__main__":
    load_dotenv()
    db = KrishaDB(db_url=os.getenv("DATABASE_URL"))
    driver = init_driver()
    
    base_url = "link to the listing page"  # Замените на реальный URL страницы с объявлениями
    page = 1

    try:
        while page <= 5: # Для примера 5 страниц
            print(f"\n--- СТРАНИЦА {page} ---")
            driver.get(f"{base_url}?page={page}")
            time.sleep(5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            cards = soup.find_all('div', class_='a-card')
            
            page_data = []
            for card in cards:
                link_el = card.find('a', class_='a-card__title')
                if not link_el: continue
                
                link = "link to the listing page" + link_el['href']  # Замените на реальный URL
                price = card.find('div', class_='a-card__price').get_text(strip=True).replace('\xa0', ' ')
                
                # Заходим внутря за деталями
                details = get_detailed_info(driver, link)
                if details:
                    details['link'] = link
                    details['price'] = price
                    page_data.append(details)
                
                time.sleep(random.uniform(1, 2))

            # Сохраняем всю страницу сразу
            db.save_apartments(page_data)
            page += 1
            
    finally:
        db.close()
        driver.quit()