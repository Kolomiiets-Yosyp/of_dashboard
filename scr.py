import sqlite3
from datetime import datetime, timedelta
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "of_dashboard.settings")  # заміни на назву твого проєкту
django.setup()
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import time
from typing import Set, Tuple, List
from threading import Thread, Lock
import queue
from dashboard.models import Users  # імпортуємо модель

UKR_MONTHS = {
    # Українські місяці
    'січ': 1, 'лют': 2, 'бер': 3, 'квіт': 4, 'трав': 5, 'черв': 6,
    'лип': 7, 'сер': 8, 'вер': 9, 'жов': 10, 'лис': 11, 'гру': 12,

    # Англійські місяці (скорочення)
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}


class NotificationTracker:
    def __init__(self):
        self.db_path = 'onlyfans_notifications.db'
        self.processed_notifications: Set[Tuple[str, str, str]] = set()
        self.data_queue = queue.Queue()
        self.stop_event = False
        self.db_lock = Lock()
        self.init_db()
        self.load_existing_notifications()

    def init_db(self):
        """Ініціалізує базу даних"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT NOT NULL,
                    password TEXT NOT NULL,
                    UNIQUE(login))
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    notification_type TEXT NOT NULL,
                    username TEXT NOT NULL,
                    content TEXT,
                    notification_time TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(user_id, notification_type, username, notification_time))
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    post_count INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(user_id, date))
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracking_link_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    click_count INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(user_id, date))
            ''')
            conn.commit()
            conn.close()

    def get_all_users(self):
        """Отримує всіх користувачів з бази даних"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT id, login, password FROM users')
                return cursor.fetchall()
            except Exception as e:
                print(f"Помилка отримання користувачів: {e}")
                return []
            finally:
                conn.close()

    def add_user(self, email: str, password: str) -> bool:
        """Додає нового користувача до бази даних"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (login, password)
                    VALUES (?, ?)
                ''', (email, password))
                conn.commit()
                return True
            except Exception as e:
                print(f"Помилка додавання користувача: {e}")
                return False
            finally:
                conn.close()

    def save_tracking_link_stats(self, user_id: int, date: str, click_count: int) -> bool:
        """Зберігає статистику переходів за трекінг-посиланнями"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO tracking_link_stats (user_id, date, click_count, recorded_at)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, date, click_count, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                print(f"✅ Збережено статистику переходів за {date}: {click_count} кліків")
                return True
            except sqlite3.IntegrityError:
                print(f"Статистика переходів за {date} вже існує в базі даних")
                return False
            finally:
                conn.close()

    def process_tracking_links_page(self, driver, user_id: int):
        """Обробляє сторінку статистики трекінг-посилань"""
        try:
            driver.get("https://onlyfans.com/my/statistics/reach/tracking-links")
            time.sleep(5)

            # Визначаємо вчорашню дату
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y-%m-%d')

            # Налаштовуємо календар (спрощений варіант)
            date_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'b-holder-options')]")))
            driver.execute_script("arguments[0].click();", date_button)
            time.sleep(1)

            custom_option = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Нетипові')]")))
            driver.execute_script("arguments[0].click();", custom_option)
            time.sleep(2)

            # Спрощена обробка календаря (може потребувати доопрацювання)
            nav_buttons = driver.find_elements(By.XPATH,
                                               "//button[contains(@class, 'g-btn m-with-round-hover m-size-sm-hover m-icon m-icon-only m-xs-size m-default-color')]")
            if len(nav_buttons) >= 2:
                for _ in range(3):
                    if nav_buttons[1].is_enabled():
                        driver.execute_script("arguments[0].click();", nav_buttons[1])
                        time.sleep(0.5)

            days = driver.find_elements(By.XPATH, "//div[contains(@class, 'v-calendar-weekly__day-label')]/span")
            for day in days:
                if day.text == str(yesterday.day):
                    driver.execute_script("arguments[0].click();", day)
                    time.sleep(1)
                    break

            apply_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'g-btn m-flat m-btn-gaps')]")))
            driver.execute_script("arguments[0].click();", apply_button)
            time.sleep(3)

            click_count_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'b-engagements-summary__item')]")))
            click_count = int(click_count_element.text.split()[0])

            self.save_tracking_link_stats(user_id, yesterday_str, click_count)

        except Exception as e:
            print(f"Помилка обробки сторінки трекінг-посилань: {e}")

    def load_existing_notifications(self):
        """Завантажує існуючі сповіщення з БД"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT notification_type, username, notification_time FROM notifications')
            self.processed_notifications = {(row[0], row[1], row[2]) for row in cursor.fetchall()}
            conn.close()

    def parse_of_date(self, date_str: str) -> datetime:
        """Конвертує дату OnlyFans у об'єкт datetime"""
        try:
            date_str = date_str.replace(',', '').strip()
            parts = date_str.split()

            # 🇺🇦 Український формат
            if parts[1].lower() in UKR_MONTHS:
                if len(parts) == 3:
                    day, month_str, time_part = parts
                    year = datetime.now().year
                elif len(parts) == 4:
                    day, month_str, year, time_part = parts
                else:
                    raise ValueError("Формат дати не відповідає українському стилю")

                hour, minute = map(int, time_part.split(':'))
                return datetime(int(year), UKR_MONTHS[month_str.lower()], int(day), hour, minute)

            # 🇬🇧 Англійський формат
            elif parts[0].lower() in UKR_MONTHS:
                if len(parts) == 4:
                    month_str, day, time_part, meridiem = parts
                    year = datetime.now().year
                elif len(parts) == 5:
                    month_str, day, year, time_part, meridiem = parts
                else:
                    raise ValueError("Формат дати не відповідає англійському стилю")

                hour, minute = map(int, time_part.split(':'))

                # AM/PM формат
                if meridiem.lower() == 'pm' and hour != 12:
                    hour += 12
                elif meridiem.lower() == 'am' and hour == 12:
                    hour = 0

                return datetime(int(year), UKR_MONTHS[month_str.lower()], int(day), hour, minute)

            else:
                raise ValueError("Невідомий місяць")

        except Exception as e:
            print(f"❌ Помилка парсингу дати '{date_str}': {e}")
            return None

    def is_within_30_days(self, date_obj: datetime) -> bool:
        """Перевіряє, чи дата знаходиться в межах останніх 30 днів"""
        if not date_obj:
            return False
        thirty_days_ago = datetime.now() - timedelta(days=30)
        return date_obj >= thirty_days_ago

    def save_notification(self, user_id: int, notification_type: str, username: str, content: str,
                          of_date_str: str) -> bool:
        """Зберігає сповіщення, якщо воно нове і за останні 30 днів"""
        notification_time = self.parse_of_date(of_date_str)
        if not notification_time or not self.is_within_30_days(notification_time):
            return False

        formatted_time = notification_time.strftime('%Y-%m-%d %H:%M:%S')
        notification_key = (notification_type, username, formatted_time)

        if notification_key in self.processed_notifications:
            return False

        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO notifications (user_id, notification_type, username, content, notification_time, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, notification_type, username, content, formatted_time,
                      datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                self.processed_notifications.add(notification_key)
                print(f"✅ Збережено: {notification_type} | {username} | {formatted_time}")
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()

    def save_post_statistics(self, user_id: int, date: str, post_count: int) -> bool:
        """Зберігає статистику постів за дату"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO post_statistics (user_id, date, post_count, recorded_at)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, date, post_count, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                print(f"✅ Збережено статистику постів за {date}: {post_count} постів")
                return True
            except sqlite3.IntegrityError:
                print(f"Статистика постів за {date} вже існує в базі даних")
                return False
            finally:
                conn.close()
    def process_page(self, driver, user_id: int, notification_type: str):
        """Обробляє конкретну сторінку сповіщень"""
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "b-notifications__list__item"))
            )

            thirty_days_ago = datetime.now() - timedelta(days=30)
            oldest_date_in_view = datetime.now()
            scroll_attempts = 0
            max_scroll_attempts = 20

            while (oldest_date_in_view > thirty_days_ago and
                   scroll_attempts < max_scroll_attempts and
                   not self.stop_event):

                notifications = driver.find_elements(By.CLASS_NAME, "b-notifications__list__item")
                if not notifications:
                    break

                oldest_date_in_view = datetime.now()
                for item in notifications:
                    try:
                        time_element = item.find_element(By.CLASS_NAME, "g-date")
                        of_date_str = time_element.find_element(By.TAG_NAME, "span").get_attribute("title")
                        notification_time = self.parse_of_date(of_date_str)
                        if notification_time and notification_time < oldest_date_in_view:
                            oldest_date_in_view = notification_time
                    except:
                        continue

                print(f"Найстаріша дата у видимому діапазоні: {oldest_date_in_view}")
                time.sleep(3)

                for item in notifications:
                    try:
                        username_element = item.find_element(By.CSS_SELECTOR, "a[href*='/']")
                        username = \
                        username_element.get_attribute("href").replace("https://onlyfans.com/", "").split('/')[0]
                        time_element = item.find_element(By.CLASS_NAME, "g-date")
                        of_date_str = time_element.find_element(By.TAG_NAME, "span").get_attribute("title")

                        content = ""
                        if notification_type == "tags":
                            try:
                                content = item.find_element(By.CLASS_NAME,
                                                            "b-notifications__list__item__text").text.strip()
                            except NoSuchElementException:
                                content = "No content"

                        self.data_queue.put((user_id, notification_type, username, content, of_date_str))
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                    except Exception as e:
                        print(f"Помилка обробки сповіщення: {e}")

                driver.execute_script("window.scrollBy(0, document.documentElement.clientWidth);")

                time.sleep(3)
                scroll_attempts += 1

                if scroll_attempts % 10 == 0:
                    print(f"Скрол #{scroll_attempts}. Найстаріша дата: {oldest_date_in_view}")

            print(f"Завершено скролінг для {notification_type}. Остання дата: {oldest_date_in_view}")

        except Exception as e:
            print(f"Помилка обробки сторінки {notification_type}: {e}")

    def scrape_profile_posts(self, driver, user_id: int):
        """Обробляє сторінку профілю для збору тегів (@) з постів"""
        try:
            user = Users.objects.get(id=user_id)
            profile_url = f"https://onlyfans.com/{user.name}"  # 🟢 URL з бази
            driver.get(profile_url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "dynamic-scroller-item"))
            )

            thirty_days_ago = datetime.now() - timedelta(days=30)
            scroll_attempts = 0
            max_scroll_attempts = 20

            while scroll_attempts < max_scroll_attempts and not self.stop_event:
                posts = driver.find_elements(By.CLASS_NAME, "dynamic-scroller-item")
                if not posts:
                    break

                for post in posts:
                    try:
                        # Отримуємо час публікації поста
                        time_element = post.find_element(By.CLASS_NAME, "b-post__date")
                        of_date_str = time_element.find_element(By.TAG_NAME, "span").get_attribute("title")
                        post_time = self.parse_of_date(of_date_str)

                        if not post_time or post_time < thirty_days_ago:
                            continue

                        # Отримуємо текст поста
                        post_text = post.find_element(By.CLASS_NAME, "b-post__text").text.strip()

                        # Знаходимо всі теги у пості
                        tag_username = next(
                            (tag.split('@')[1].split()[0] for tag in post_text.split() if tag.startswith('@')),
                            None
                        )

                        # Якщо тег знайдено — зберігаємо
                        if tag_username:
                            self.save_post_tag(
                                user_id=user_id,
                                post_text=post_text,
                                tag_username=tag_username,
                                post_time=post_time
                            )

                    except Exception as e:
                        print(f"Помилка обробки поста: {e}")
                        continue

                # Скролимо сторінку
                driver.execute_script("window.scrollBy(0, document.documentElement.clientWidth);")
                time.sleep(3)
                scroll_attempts += 1

                if scroll_attempts % 10 == 0:
                    print(f"Скрол #{scroll_attempts}")

            print("Завершено збір тегів з профілю")

        except Exception as e:
            print(f"Помилка обробки сторінки профілю: {e}")

    def save_post_tag(self, user_id: int, post_text: str, tag_username: str, post_time: datetime):
        """Зберігає тег в базу даних без використання Django ORM"""
        conn = sqlite3.connect('onlyfans_notifications.db')
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO post_tags (user_id, post_text, tag_username, post_time, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, post_text, tag_username, post_time, datetime.now()))
            conn.commit()
            print(f"✅ Збережено тег: @{tag_username} | {post_time}")
        except sqlite3.Error as e:
            print(f"Помилка збереження тега: {e}")
        finally:
            conn.close()

    def process_queue_page(self, driver, user_id: int):
        """Обробляє сторінку черги для отримання кількості запланованих постів"""
        try:
            driver.get("https://onlyfans.com/my/queue")
            time.sleep(5)

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "v-calendar-weekly"))
            )

            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')
            scheduled_posts = {}

            post_elements = driver.find_elements(By.XPATH,
                                                 "//div[contains(@class, 'v-event') and contains(@class, 'post')]")

            for post_element in post_elements:
                try:
                    post_date = post_element.get_attribute("data-date")
                    count_element = post_element.find_element(By.CLASS_NAME, "v-event-summary")
                    post_count = int(count_element.text.strip().split()[0])
                    scheduled_posts[post_date] = post_count
                except Exception as e:
                    print(f"Помилка обробки елементу поста: {e}")
                    continue

            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scheduled_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        post_count INTEGER NOT NULL,
                        recorded_at TEXT NOT NULL,
                        UNIQUE(user_id, date))
                ''')

                for date, count in scheduled_posts.items():
                    try:
                        cursor.execute('''
                            INSERT INTO scheduled_posts (user_id, date, post_count, recorded_at)
                            VALUES (?, ?, ?, ?)
                        ''', (user_id, date, count, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                        print(f"✅ Збережено заплановані пости на {date}: {count} постів")
                    except sqlite3.IntegrityError:
                        print(f"Дані про заплановані пости на {date} вже існують в базі")

                conn.commit()
                conn.close()

            if today_str in scheduled_posts:
                print(f"На сьогодні ({today_str}) заплановано {scheduled_posts[today_str]} постів")
            else:
                print(f"На сьогодні ({today_str}) немає запланованих постів")

            return True

        except Exception as e:
            print(f"Помилка обробки сторінки черги: {e}")
            return False

    def process_engagement_page(self, driver, user_id: int):
        """Обробляє сторінку статистики для отримання кількості постів за вчора"""
        try:
            driver.get("https://onlyfans.com/my/statistics/engagement/posts")
            time.sleep(5)

            date_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'b-holder-options')]")))
            driver.execute_script("arguments[0].click();", date_button)
            time.sleep(1)

            custom_option = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Нетипові')]")))
            driver.execute_script("arguments[0].click();", custom_option)
            time.sleep(2)

            yesterday = datetime.now() - timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y-%m-%d')

            nav_buttons = driver.find_elements(By.XPATH,
                                               "//button[contains(@class, 'g-btn m-with-round-hover m-size-sm-hover m-icon m-icon-only m-xs-size m-default-color')]")
            if len(nav_buttons) >= 2:
                for _ in range(3):
                    if nav_buttons[1].is_enabled():
                        driver.execute_script("arguments[0].click();", nav_buttons[1])
                        time.sleep(0.5)

            days = driver.find_elements(By.XPATH, "//div[contains(@class, 'v-calendar-weekly__day-label')]/span")
            for day in days:
                if day.text == str(yesterday.day):
                    driver.execute_script("arguments[0].click();", day)
                    time.sleep(1)
                    break

            apply_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'g-btn m-flat m-btn-gaps')]")))
            driver.execute_script("arguments[0].click();", apply_button)
            time.sleep(3)

            post_count_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'b-engagements-summary__item')]")))
            post_count = int(post_count_element.text.split()[0])

            self.save_post_statistics(user_id, yesterday_str, post_count)

        except Exception as e:
            print(f"Помилка обробки сторінки статистики: {e}")

    def data_processor(self):
        """Обробляє дані з черги"""
        while not self.stop_event:
            try:
                data = self.data_queue.get(timeout=1)
                user_id, notification_type, username, content, of_date_str = data
                self.save_notification(user_id, notification_type, username, content, of_date_str)
                self.data_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Помилка обробки даних: {e}")


def login_to_onlyfans(driver, email: str, password: str) -> bool:
    """Виконує вхід на OnlyFans"""
    try:
        driver.get("https://onlyfans.com/my/notifications/tags")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "b-loginreg__form"))
        )

        # Введення email
        email_field = driver.find_element(By.XPATH, "//input[@name='email']")
        driver.execute_script("arguments[0].scrollIntoView();", email_field)
        email_field.click()
        email_field.clear()
        email_field.send_keys(email)

        # Введення пароля
        password_field = driver.find_element(By.XPATH, "//input[@name='password']")
        driver.execute_script("arguments[0].scrollIntoView();", password_field)
        password_field.click()
        password_field.clear()
        password_field.send_keys(password)
        print("!!!!!!!")
        # Клік на кнопку входу
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        driver.execute_script("arguments[0].click();", login_button)

        # Очікування завантаження списку сповіщень
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "vue-recycle-scroller__item-wrapper"))
        )
        return True
    except Exception as e:
        print(f"Помилка входу: {e}")
        return False

def process_user_account(tracker, user_id: int, email: str, password: str):
    """Обробляє один акаунт користувача"""
    print(f"\n=== Початок обробки акаунта {email} ===")

    options = webdriver.ChromeOptions()
    #options.add_argument('--remote-debugging-port=9222')  # Відкриває порт для дебагу
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    #options.add_argument('--disable-gpu')
    options.add_argument('--start-maximized')
    #options.add_argument('--headless=new')

    driver = webdriver.Chrome(options=options)

    try:
        if not login_to_onlyfans(driver, email, password):
            print(f"Не вдалося увійти для акаунта {email}, пропускаємо")
            return

        print(f"Успішний вхід для {email}. Початок збору даних...")
        tracker.scrape_profile_posts(driver, user_id)
        pages = [
            ("subscribed", "https://onlyfans.com/my/notifications/subscribed"),
            ("tags", "https://onlyfans.com/my/notifications/tags")
        ]

        for page_type, page_url in pages:
            print(f"Обробка {page_type} для {email}...")
            driver.get(page_url)
            time.sleep(5)
            tracker.process_page(driver, user_id, page_type)

        print(f"\nЗбір статистики для {email}...")
        tracker.process_tracking_links_page(driver, user_id)
        tracker.process_engagement_page(driver, user_id)
        tracker.process_queue_page(driver, user_id)

        print(f"\n=== Завершено обробку акаунта {email} ===")

    except Exception as e:
        print(f"Помилка при обробці акаунта {email}: {e}")
    finally:
        driver.quit()
        time.sleep(2)  # Невелика пауза між акаунтами


def main():
    tracker = NotificationTracker()

    # Запускаємо обробник даних в окремому потоці
    processor_thread = Thread(target=tracker.data_processor, daemon=True)
    processor_thread.start()

    try:
        # Отримуємо всіх користувачів з БД
        all_users = tracker.get_all_users()
        if not all_users:
            print("Не знайдено жодного користувача в базі даних")
            return

        print(f"Знайдено {len(all_users)} користувачів для обробки")

        # Обробляємо кожного користувача послідовно
        for user_id, email, password in all_users:
            process_user_account(tracker, user_id, email, password)

    except KeyboardInterrupt:
        print("\nЗавершення роботи через Ctrl+C...")
        tracker.stop_event = True
    except Exception as e:
        print(f"Критична помилка: {e}")
        tracker.stop_event = True
    finally:
        tracker.stop_event = True
        processor_thread.join()
        print("Роботу завершено, ресурси звільнено")


if __name__ == "__main__":
    main()