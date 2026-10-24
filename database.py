import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import execute_values

class KrishaDB:
    def __init__(self, db_url=None):
        load_dotenv()
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("Подключено к БД.")
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            raise e

    def create_tables(self):
        # 1 таблица: количество квартир по городам
        # 2 таблица: описание квартиры (комнатность, цена, местоположение, площадь)
        create_query = """
        CREATE TABLE IF NOT EXISTS cities_apartment_stats (
            id SERIAL PRIMARY KEY,
            city VARCHAR(100) UNIQUE NOT NULL,
            apartments_count INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS apartments (
            id SERIAL PRIMARY KEY,
            rooms VARCHAR(50),
            price VARCHAR(100),
            city VARCHAR(100),
            location TEXT,
            area VARCHAR(50),
            link TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            self.cursor.execute(create_query)
            self.conn.commit()
            print("Таблицы успешно инициализированы.")
        except Exception as e:
            print(f"Ошибка создания таблиц: {e}")
            self.conn.rollback()

    def save_apartments(self, data_list):
        if not data_list:
            return
        
        insert_query = """
        INSERT INTO apartments (rooms, price, city, location, area, link)
        VALUES %s
        ON CONFLICT (link) DO UPDATE SET
            rooms = EXCLUDED.rooms,
            price = EXCLUDED.price,
            city = EXCLUDED.city,
            location = EXCLUDED.location,
            area = EXCLUDED.area;
        """
        
        rows = [
            (
                d.get('rooms', 'не указано'),
                d.get('price', 'не указано'),
                d.get('city', 'не указано'),
                d.get('location', 'не указано'),
                d.get('area', 'не указано'),
                d['link']
            )
            for d in data_list
        ]

        try:
            execute_values(self.cursor, insert_query, rows)
            
            # Обновляем таблицу 1 (статистика по городам)
            self.update_city_counts()
            
            self.conn.commit()
            print(f"Сохранено объектов: {len(rows)}")
        except Exception as e:
            print(f"Ошибка вставки: {e}")
            self.conn.rollback()

    def update_city_counts(self):
        """Пересчитывает и обновляет 1-ю таблицу: количество квартир по городам"""
        query = """
        INSERT INTO cities_apartment_stats (city, apartments_count, updated_at)
        SELECT 
            city, 
            COUNT(*) as apartments_count, 
            CURRENT_TIMESTAMP
        FROM apartments
        GROUP BY city
        ON CONFLICT (city) DO UPDATE SET
            apartments_count = EXCLUDED.apartments_count,
            updated_at = EXCLUDED.updated_at;
        """
        self.cursor.execute(query)

    def close(self):
        if self.cursor: 
            self.cursor.close()
        if self.conn: 
            self.conn.close()
