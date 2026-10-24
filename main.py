import time
import random
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from database import KrishaDB

def safe_get_text(element, default="не указано"):
    return element.get_text(strip=True) if element else default

def init_driver():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return uc.Chrome(options=options, use_subprocess=True)

def get_detailed_info(driver, url):
    """Извлекает комнатность, стоимость, местоположение и площадь со страницы объявления"""
    try:
        driver.get(url)
        time.sleep(random.uniform(2.5, 4.0))
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        res = {
            'rooms': 'не указано',
            'price': 'не указано',
            'city': 'не указано',
            'location': 'не указано',
            'area': 'не указано',
            'link': url
        }

        # 1. Стоимость
        price_el = soup.find('div', class_='offer__price')
        if price_el:
            res['price'] = price_el.get_text(strip=True).replace('\xa0', ' ')

        # 2. Комнатность (из заголовка или характеристик)
        title_el = soup.find('div', class_='offer__advert-title')
        if title_el and title_el.h1:
            title_text = title_el.h1.get_text(strip=True)
            match_rooms = re.search(r'(\d+[\s\-]комнатная|\bстудия\b)', title_text, re.IGNORECASE)
            if match_rooms:
                res['rooms'] = match_rooms.group(1)

        # 3. Местоположение и город (из хлебных крошек или блока адреса)
        breadcrumbs = soup.find('ul', class_='breadcrumbs')
        if breadcrumbs:
            crumbs = [li.get_text(strip=True) for li in breadcrumbs.find_all('li')]
            for c in crumbs:
                if 'в ' in c.lower():
                    res['city'] = re.sub(r'^[Нн]едвижимость\s+в\s+', '', c).strip()
                    break

        location_el = soup.find('div', class_='offer__location')
        if location_el:
            res['location'] = location_el.get_text(strip=True)
            if res['city'] == 'не указано':
                res['city'] = res['location'].split(',')[0].strip()

        # 4. Площадь и альтернативные параметры
        square_el = soup.find('div', attrs={'data-name': 'live.square'})
        if square_el:
            term = square_el.find('div', class_='offer__info-term')
            if term:
                res['area'] = term.get_text(strip=True)

        info_items = soup.find_all('div', class_='offer__info-item')
        for item in info_items:
            title = safe_get_text(item.find('div', class_='offer__info-title')).lower()
            val = safe_get_text(item.find('div', class_='offer__info-term'))
            if 'площадь' in title and res['area'] == 'не указано':
                res['area'] = val
            elif 'комнат' in title and res['rooms'] == 'не указано':
                res['rooms'] = val

        return res
    except Exception as e:
        print(f"Ошибка при обработке {url}: {e}")
        return None

if __name__ == "__main__":
    load_dotenv()
    db = KrishaDB()
    driver = init_driver()
    
    # URL страницы поиска
    base_url = "https://krisha.kz/prodazha/kvartiry/"
    max_pages = 3  # Количество страниц для обхода

    try:
        for page in range(1, max_pages + 1):
            page_url = f"{base_url}?page={page}"
            print(f"\n--- Парсинг страницы {page}: {page_url} ---")
            driver.get(page_url)
            time.sleep(4)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            cards = soup.find_all('div', class_='a-card')
            
            page_data = []
            for card in cards:
                link_el = card.find('a', class_='a-card__title')
                if not link_el or not link_el.get('href'):
                    continue
                
                href = link_el['href']
                full_link = href if href.startswith('http') else f"https://krisha.kz{href}"
                
                print(f"Обработка объявления: {full_link}")
                details = get_detailed_info(driver, full_link)
                if details:
                    page_data.append(details)
                
                time.sleep(random.uniform(1.0, 2.0))

            if page_data:
                db.save_apartments(page_data)
                
    finally:
        db.close()
        driver.quit()
