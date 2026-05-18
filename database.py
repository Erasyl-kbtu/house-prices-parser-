import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import execute_values

class KrishaDB:
    def __init__(self, db_url):
        load_dotenv()
        db_url = os.getenv("DATABASE_URL")
        self.db_url = db_url
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_table()

    def connect(self):
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("Подключено к БД.")
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            raise e

    def create_table(self):
        # Новая структура: цена, площадь, год, район, этаж, комнаты
        create_query = """

        CREATE TABLE IF NOT EXISTS krisha_apartments (
            id SERIAL PRIMARY KEY,
            price_text VARCHAR(100),
            area VARCHAR(50),
            year_built VARCHAR(50),
            floor VARCHAR(50),
            link TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            self.cursor.execute(create_query)
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка таблицы: {e}")
            self.conn.rollback()

    def save_apartments(self, data_list):
        if not data_list: return
        
        insert_query = """
        INSERT INTO krisha_apartments (price_text, area, year_built, district, floor, rooms, link)
        VALUES %s
        ON CONFLICT (link) DO NOTHING;
        """
        
        # Готовим данные в правильном порядке
        rows = [
            (d['price'], d['area'], d['year_built'], d['district'], d['floor'], d['rooms'], d['link'])
            for d in data_list
        ]

        try:
            execute_values(self.cursor, insert_query, rows)
            self.conn.commit()
            print(f"Сохранено объектов: {len(rows)}")
        except Exception as e:
            print(f"Ошибка вставки: {e}")
            self.conn.rollback()

    def close(self):
        if self.cursor: self.cursor.close()
        if self.conn: self.conn.close()