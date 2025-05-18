import asyncio
import random
import time
import os

from playwright.async_api import async_playwright
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from typing import Set, Tuple, List

UKR_MONTHS = {
    'січ': 1, 'лют': 2, 'бер': 3, 'квіт': 4, 'трав': 5, 'черв': 6,
    'лип': 7, 'серп': 8, 'вер': 9, 'жов': 10, 'лис': 11, 'гру': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}
import psycopg2
from psycopg2.extras import RealDictCursor
# === Клас для роботи з БД ===
class NotificationTracker:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname='onlyfans',
            user='ofuser',
            password='ofpass123',
            host='185.177.239.31',
            port='5432'
        )
        self.conn.autocommit = True
        self.processed_notifications: Set[Tuple[str, str, str]] = set()
        self.db_lock = Lock()
        self.init_db()

    def init_db(self):
        with self.conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    login TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    notification_type TEXT NOT NULL,
                    username TEXT NOT NULL,
                    content TEXT,
                    notification_time TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(user_id, notification_type, username, notification_time)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_statistics (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    date TEXT NOT NULL,
                    post_count INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(user_id, date)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracking_link_stats (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    date TEXT NOT NULL,
                    click_count INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(user_id, date)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_tags (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    post_text TEXT NOT NULL,
                    tag_username TEXT NOT NULL,
                    post_time TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
            ''')

    def get_all_users(self):
        with self.conn.cursor() as cursor:
            try:
                cursor.execute('SELECT id, login, password FROM users')
                return cursor.fetchall()
            except Exception as e:
                print(f"Помилка отримання користувачів: {e}")
                return []

    def add_user(self, email: str, password: str) -> bool:
        with self.conn.cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO users (login, password)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                ''', (email, password))
                return True
            except Exception as e:
                print(f"Помилка додавання користувача: {e}")
                return False

    def save_notification(self, user_id: int, notification_type: str, username: str, content: str, of_date_str: str) -> bool:
        notification_time = self.parse_of_date(of_date_str)
        if not notification_time or not self.is_within_30_days(notification_time):
            return False
        formatted_time = notification_time.strftime('%Y-%m-%d %H:%M:%S')
        notification_key = (notification_type, username, formatted_time)
        if notification_key in self.processed_notifications:
            return False
        with self.conn.cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO notifications (user_id, notification_type, username, content, notification_time, recorded_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', (
                    user_id, notification_type, username, content,
                    formatted_time, datetime.now()
                ))
                self.processed_notifications.add(notification_key)
                print(f"✅ Збережено: {notification_type} | {username} | {formatted_time}")
                return True
            except Exception as e:
                print(f"❌ Помилка збереження нотифікації: {e}")
                return False
    def save_shared_post(self, user_id: int, date: str ,count: int) -> bool:
        with self.conn.cursor() as cursor:
            cursor.execute('''
                        INSERT INTO scheduled_posts (user_id, date, post_count, recorded_at)
                        VALUES (%s, %s, %s, %s)
                    ''', (user_id, date, count, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


    def save_post_statistics(self, user_id: int, date: str, post_count: int) -> bool:
        with self.conn.cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO post_statistics (user_id, date, post_count, recorded_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, date) DO NOTHING
                ''', (user_id, date, post_count, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                print(f"✅ Збережено статистику постів за {date}: {post_count} постів")
                return True
            except Exception as e:
                print(f"❌ Помилка збереження статистики постів: {e}")
                return False

    def save_tracking_link_stats(self, user_id: int, date: str, click_count: int) -> bool:
        with self.conn.cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO tracking_link_stats (user_id, date, click_count, recorded_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, date) DO NOTHING
                ''', (user_id, date, click_count, datetime.now()))
                print(f"✅ Збережено статистику переходів за {date}: {click_count} кліків")
                return True
            except Exception as e:
                print(f"❌ Помилка збереження статистики переходів: {e}")
                return False

    def save_post_tag(self, user_id: int, post_text: str, tag_username: str, post_time: datetime):
        with self.conn.cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO post_tags (user_id, post_text, tag_username, post_time, recorded_at)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (
                    user_id, post_text, tag_username,
                    post_time.strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now()
                ))
                print(f"✅ Збережено тег: @{tag_username} | {post_time}")
            except Exception as e:
                print(f"❌ Помилка збереження тега: {e}")

    def parse_of_date(self, date_str: str) -> datetime:
        try:
            date_str = date_str.replace(',', '').strip()
            parts = date_str.split()
            if len(parts) < 2:
                return None
            if parts[1].lower() in UKR_MONTHS:
                if len(parts) == 3:
                    day, month_str, time_part = parts
                    year = datetime.now().year
                elif len(parts) == 4:
                    day, month_str, year, time_part = parts
                else:
                    return None
                hour, minute = map(int, time_part.split(':'))
                return datetime(int(year), UKR_MONTHS[month_str.lower()], int(day), hour, minute)
            elif parts[0].lower() in UKR_MONTHS:
                if len(parts) == 4:
                    month_str, day, time_part, meridiem = parts
                    year = datetime.now().year
                elif len(parts) == 5:
                    month_str, day, year, time_part, meridiem = parts
                else:
                    return None
                hour, minute = map(int, time_part.split(':'))
                if meridiem.lower() == 'pm' and hour != 12:
                    hour += 12
                elif meridiem.lower() == 'am' and hour == 12:
                    hour = 0
                return datetime(int(year), UKR_MONTHS[month_str.lower()], int(day), hour, minute)
            else:
                return None
        except Exception as e:
            print(f"❌ Помилка парсингу дати '{date_str}': {e}")
            return None

    def is_within_30_days(self, date_obj: datetime) -> bool:
        if not date_obj:
            return False
        return date_obj >= (datetime.now() - timedelta(days=30))

# === Клас для роботи з Playwright ===
class OnlyFansScraper:
    def __init__(self, tracker: NotificationTracker):
        self.tracker = tracker
        self.contexts_dir = "browser_contexts"
        if not os.path.exists(self.contexts_dir):
            os.makedirs(self.contexts_dir)

    def get_context_path(self, email: str) -> str:
        """Отримати шлях до файлу контексту для конкретного email"""
        return os.path.join(self.contexts_dir, f"{email.replace('@', '_at_')}.json")

    async def save_context(self, context, email: str):
        """Зберегти контекст браузера"""
        try:
            await context.storage_state(path=self.get_context_path(email))
            print(f"✅ Контекст збережено для {email}")
        except Exception as e:
            print(f"❌ Помилка збереження контексту для {email}: {e}")

    async def load_context(self, browser, email: str):
        """Завантажити контекст браузера"""
        context_path = self.get_context_path(email)
        if os.path.exists(context_path):
            try:
                context = await browser.new_context(storage_state=context_path)
                print(f"✅ Контекст завантажено для {email}")
                return context
            except Exception as e:
                print(f"❌ Помилка завантаження контексту для {email}: {e}")
        return None

    async def ensure_logged_in(self, page, email: str, password: str) -> bool:
        """Перевірити чи користувач залогінений, якщо ні - залогінити"""
        try:
            # Перевіряємо чи ми на головній сторінці
            current_url = page.url
            if "onlyfans.com" not in current_url:
                await page.goto('https://onlyfans.com/', timeout=80000)
            
            # Перевіряємо наявність аватара (ознака успішного логіну)
            try:
                await page.wait_for_selector('.g-avatar', timeout=5000)
                print(f"✅ Користувач {email} вже залогінений")
                return True
            except:
                print(f"⚠️ Користувач {email} не залогінений, виконуємо логін")
                return await self.login(page, email, password)
        except Exception as e:
            print(f"❌ Помилка перевірки логіну для {email}: {e}")
            return False

    async def login(self, page, email: str, password: str) -> bool:
        try:
            await page.goto('https://onlyfans.com/?return_to=%2Flogin', timeout=80000)
            await page.wait_for_selector('input[name="email"]', timeout=80000)
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button[at-attr="submit"]:not([disabled])')
            try:
                await page.wait_for_selector('.g-avatar', timeout=80000)
            except:
                print("Login failed")
                return False
            return True
        except Exception as e:
            print(f"Login error: {e}")
            return False

    async def scrape_profile_posts(self, page, user_id: int):
        import re
        try:
            # Перейти на сторінку статистики постів (або профілю, якщо треба)
            await page.goto('https://onlyfans.com/my/statistics/engagement/posts', timeout=60000)
            await page.wait_for_selector('.b-table', timeout=10000)

            # Скролимо до кінця, щоб завантажити всі пости
            print("Scrolling to load all posts...")
            scroll_attempts = 0
            max_scroll_attempts = 2
            last_height = 0
            while scroll_attempts < max_scroll_attempts:
                current_height = await page.evaluate('document.body.scrollHeight')
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)
                new_height = await page.evaluate('document.body.scrollHeight')
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                    last_height = new_height
                print(f"Scroll attempt {scroll_attempts}/{max_scroll_attempts} | Page height: {new_height}px")

            # Збір тегів з усіх постів
            print("\nCollecting data from all loaded posts...")
            rows = await page.query_selector_all('tbody tr.m-responsive__reset-pb')
            for row in rows:
                try:
                    date_element = await row.query_selector('.b-top-statistic__link strong')
                    post_date = None
                    if date_element:
                        date_str = await date_element.inner_text()
                        post_date = self.tracker.parse_of_date(date_str)

                    text_element = await row.query_selector('.b-top-statistic__text p')
                    if text_element:
                        text = await text_element.inner_text()
                        found_usernames = re.findall(r'@([a-zA-Z0-9_.]+)', text)
                        if found_usernames:
                            username = found_usernames[0].lower()  # Беремо перший тег
                            # Зберігаємо тег у БД через NotificationTracker
                            self.tracker.save_post_tag(user_id, text, username.lower(), post_date)
                except Exception as e:
                    print(f"Error processing post: {e}")
            print(f"\nCompleted. Found tags in {len(rows)} posts.")
        except Exception as e:
            print(f"Error in scrape_profile_posts: {e}")

    async def process_notifications(self, page, user_id: int, notification_type: str, url: str):
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_selector('.b-notifications__list__item', timeout=20000)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            oldest_date_in_view = datetime.now()
            scroll_attempts = 0
            max_scroll_attempts = 20
            while oldest_date_in_view > thirty_days_ago and scroll_attempts < max_scroll_attempts:
                notifications = await page.query_selector_all('.b-notifications__list__item')
                if not notifications:
                    break
                oldest_date_in_view = datetime.now()
                for item in notifications:
                    try:
                        time_element = await item.query_selector('.g-date span')
                        of_date_str = await time_element.get_attribute('title') if time_element else None
                        notification_time = self.tracker.parse_of_date(of_date_str) if of_date_str else None
                        if notification_time and notification_time < oldest_date_in_view:
                            oldest_date_in_view = notification_time
                    except Exception:
                        continue
                for item in notifications:
                    try:
                        username_element = await item.query_selector('a[href*="/"]')
                        username = None
                        if username_element:
                            href = await username_element.get_attribute('href')
                            username = href.replace('https://onlyfans.com/', '').split('/')[0]
                        time_element = await item.query_selector('.g-date span')
                        of_date_str = await time_element.get_attribute('title') if time_element else None
                        content = ""
                        if notification_type == "tags":
                            content_el = await item.query_selector('.b-notifications__list__item__text')
                            content = await content_el.inner_text() if content_el else "No content"
                        if username and of_date_str:
                            self.tracker.save_notification(user_id, notification_type, username, content, of_date_str)
                    except Exception as e:
                        print(f"Помилка обробки сповіщення: {e}")
                await page.evaluate('window.scrollBy(0, document.documentElement.clientWidth)')
                await asyncio.sleep(3)
                scroll_attempts += 1
                if scroll_attempts % 10 == 0:
                    print(f"Скрол #{scroll_attempts}. Найстаріша дата: {oldest_date_in_view}")
            print(f"Завершено скролінг для {notification_type}. Остання дата: {oldest_date_in_view}")
        except Exception as e:
            print(f"Помилка обробки сторінки {notification_type}: {e}")

    async def process_tracking_links_page(self, page, user_id: int):
        try:
            import re

            await page.goto("https://onlyfans.com/my/statistics/reach/tracking-links", timeout=60000)

            await page.wait_for_selector('.b-holder-options', timeout=20000)
            await asyncio.sleep(1)
            # 1. Встановлюємо період "Весь час"
            dropdown_button = await page.query_selector('button.b-holder-options')
            if not dropdown_button:
                raise Exception("Не знайдено кнопку вибору періоду")

            await dropdown_button.click()
            await asyncio.sleep(2)

            all_time_option = await page.query_selector('button.dropdown-item:has-text("Весь час")')
            if not all_time_option:
                raise Exception("Не знайдено опцію 'Весь час'")

            await all_time_option.click()
            await asyncio.sleep(2)  # Чекаємо оновлення даних

            # 2. Отримуємо всі рядки таблиці
            rows = await page.query_selector_all('tbody tr.m-responsive__reset-pb')
            if not rows:
                print("Не знайдено жодного рядка в таблиці")
                return

            # 3. Обробляємо кожен рядок
            for row in rows:
                try:
                    # Отримуємо всі комірки рядка
                    cells = await row.query_selector_all('td')
                    if len(cells) < 5:  # Перевіряємо, що є всі необхідні стовпці
                        continue

                    # 3.1. Отримуємо назву посилання (1-й стовпець)
                    link_name_element = await cells[0].query_selector('strong')
                    link_name = await link_name_element.inner_text() if link_name_element else "Невідоме посилання"

                    # 3.2. Отримуємо дату (2-й стовпець)
                    date_element = await cells[1].query_selector('span[title]')
                    date_str = await date_element.inner_text() if date_element else None
                    if not date_str:
                        date_str = await cells[1].inner_text()
                    date_str = date_str.strip()

                    # Обробляємо дату
                    if not re.search(r'\d{1,2}:\d{2}', date_str):  # Якщо немає часу
                        date_str += " 00:00"

                    date_obj = self.tracker.parse_of_date(date_str)
                    if not date_obj:
                        print(f"Не вдалося розпізнати дату: {date_str}")
                        continue

                    formatted_date = date_obj.strftime('%Y-%m-%d')

                    # 3.3. Отримуємо кліки (4-й стовпець)
                    clicks_text = await cells[3].inner_text()
                    clicks = int(re.sub(r'[^\d]', '', clicks_text)) if clicks_text else 0

                    # 3.4. Отримуємо інші дані (за потреби)
                    # Наприклад, 5-й стовпець містить додаткову інформацію
                    additional_info = await cells[4].inner_text()

                    # Зберігаємо дані
                    if clicks > 0:
                        self.tracker.save_tracking_link_stats(user_id, formatted_date, clicks)
                        print(f"Збережено: {link_name} - {formatted_date} - {clicks} кліків")

                except Exception as e:
                    print(f"Помилка обробки рядка: {str(e)[:200]}")
                    continue

        except Exception as e:
            print(f"Помилка обробки сторінки трекінг-посилань: {str(e)[:200]}")

    async def process_engagement_page(self, page, user_id: int):
        try:
            await asyncio.sleep(6)
            await page.goto("https://onlyfans.com/my/statistics/engagement/posts", timeout=60000)

            yesterday = datetime.now() - timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y-%m-%d')
            post_count_element = await page.query_selector('.b-engagements-summary__item')
            post_count = 0
            if post_count_element:
                text = await post_count_element.inner_text()
                try:
                    post_count = int(text.split()[0])
                except Exception:
                    post_count = 0
            self.tracker.save_post_statistics(user_id, yesterday_str, post_count)
        except Exception as e:
            print(f"Помилка обробки сторінки статистики: {e}")

    async def process_queue_page(self, page, user_id: int):
        try:
            await asyncio.sleep(3)
            await page.goto("https://onlyfans.com/my/queue", timeout=60000)

            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')
            scheduled_posts = {}
            time.sleep(2)
            post_elements = await page.query_selector_all('div.v-event.post')
            for post_element in post_elements:
                try:
                    post_date = await post_element.get_attribute("data-date")
                    count_element = await post_element.query_selector('.v-event-summary')
                    post_count = 0
                    if count_element:
                        try:
                            post_count = int((await count_element.inner_text()).strip().split()[0])
                        except Exception:
                            post_count = 0
                    if post_date:
                        scheduled_posts[post_date] = post_count
                except Exception as e:
                    print(f"Помилка обробки елементу поста: {e}")
                    continue
            # Збереження у БД
            for date, count in scheduled_posts.items():
                try:
                    self.tracker.save_shared_post(user_id, date, count)
                except Exception as e:
                    print(e)
            if today_str in scheduled_posts:
                print(f"На сьогодні ({today_str}) заплановано {scheduled_posts[today_str]} постів")
            else:
                print(f"На сьогодні ({today_str}) немає запланованих постів")
            return True
        except Exception as e:
            print(f"Помилка обробки сторінки черги: {e}")
            return False

    async def process_subscribed_notifications(self, page, user_id: int, notification_type: str, url: str, days_limit: int = 30):
        try:
            await asyncio.sleep(2)
            await page.goto(url, timeout=60000)
            await page.wait_for_selector('[data-v-0e3f72a6]', timeout=20000)
            last_index = -1
            processed_indices = set()
            start_time = datetime.now()
            date_threshold = (datetime.now() - timedelta(days=days_limit)).date()

            while True:
                await page.wait_for_selector('[data-v-0e3f72a6][data-index]')
                # 1. Збір поточних даних
                current_items = await page.query_selector_all('[data-v-0e3f72a6][data-index]')
                new_data = []

                for item in current_items:
                    try:
                        index = int(await item.get_attribute('data-index'))
                        if index in processed_indices:
                            continue

                        # Отримання даних з елементу
                        username = await item.eval_on_selector('.g-user-name',
                                                               'el => el?.textContent?.trim() || "Невідомий"')
                        userlink = await item.eval_on_selector('.g-user-username',
                                                               'el => el?.textContent?.trim() || ""')
                        date_str = await item.eval_on_selector('.g-date span', 'el => el?.title || ""')

                        # Парсинг дати
                        try:
                            item_date = self.tracker.parse_of_date(date_str).date()
                            if item_date < date_threshold:
                                print(f"Досягнуто {days_limit}-денний ліміт (остання дата: {item_date})")
                                return True
                        except:
                            continue

                        new_data.append({
                            'index': index,
                            'username': username,
                            'userlink': userlink,
                            'date': date_str
                        })
                        processed_indices.add(index)

                    except Exception as e:
                        print(f"Помилка обробки елементу {index}: {e}")

                # 2. Збереження в БД
                if new_data:
                    for data in new_data:
                        self.tracker.save_notification(
                            user_id=user_id,
                            username=data['userlink'][1:],
                            notification_type=notification_type,
                            content=f"{data['username']} ({data['userlink']}) - {data['date']}",
                            of_date_str=data['date']
                        )
                    print(f"Додано {len(new_data)} нових записів (індекси: {[d['index'] for d in new_data]})")

                # 3. Визначення останнього індексу
                if current_items:
                    last_item = current_items[-1]
                    last_index = int(await last_item.get_attribute('data-index'))
                    print(f"Останній індекс на сторінці: {last_index}")

                # 4. Скрол до останнього елементу
                if current_items:
                    await last_item.scroll_into_view_if_needed()

                    # Додаткова перевірка на нові елементи
                    #new_height = await page.evaluate('document.body.scrollHeight')
                    #await page.evaluate(f'window.scrollTo(0, {new_height})')
                    await asyncio.sleep(1)
                else:
                    break

                # 5. Перевірка на завершення
                current_date = datetime.now().date()
                if (current_date - start_time.date()).days > days_limit:
                    print(f"Досягнуто ліміт у {days_limit} днів")
                    break

            print(f"Скрипт завершено. Усього оброблено {len(processed_indices)} підписок")
            return True

        except Exception as e:
            print(f"Критична помилка: {str(e)}")
            return False

# === Основна асинхронна функція ===
async def main():
    tracker = NotificationTracker()
    scraper = OnlyFansScraper(tracker)
    all_users = tracker.get_all_users()

    if not all_users:
        print("Не знайдено жодного користувача в базі даних")
        return

    async def process_account(user_id, email, password):
        """Обробка одного акаунту в окремому браузері"""
        async with async_playwright() as p:
            # Створюємо окремий браузер для кожного акаунту
            browser = await p.chromium.launch(headless=False, timeout=60000)
            
            # Намагаємося завантажити збережений контекст
            context = await scraper.load_context(browser, email)
            if not context:
                context = await browser.new_context()
            
            page = await context.new_page()

            try:
                # Перевіряємо/відновлюємо логін
                if not await scraper.ensure_logged_in(page, email, password):
                    print(f"⚠️ Помилка логіну: {email}")
                    return

                # Зберігаємо контекст після успішного логіну
                await scraper.save_context(context, email)

                print(f"✅ Успішний логін для {email}")
                # Створення вкладок з паузами
                await asyncio.sleep(random.uniform(1, 6))
                # Створюємо додаткові вкладки для паралельної обробки
                notifications_page = await context.new_page()
                analytics_page = await context.new_page()
                process_engagement = await context.new_page()
                process_queue = await context.new_page()
                tracing_page = await context.new_page()
                process_tag = await context.new_page()
                # Запускаємо обробку паралельно
                await asyncio.gather(
                    scraper.process_tracking_links_page(tracing_page, user_id),
                    scraper.process_queue_page(process_queue, user_id),
                    scraper.process_engagement_page(process_engagement, user_id),
                    scraper.process_subscribed_notifications(notifications_page, user_id, "subscribed", "https://onlyfans.com/my/notifications/subscribed"),
                    scraper.scrape_profile_posts(analytics_page, user_id),

                    scraper.process_subscribed_notifications(process_tag, user_id, "tags", "https://onlyfans.com/my/notifications/tags"),
                    return_exceptions=True
                )

                print(f"✅ Успішно оброблено {email}")

                # Залишаємо браузер відкритим
                while True:
                    await asyncio.sleep(3*60)  # Чекаємо 3 хвилини перед наступною перевіркою
                    # Перевіряємо чи все ще залогінені
                    if not await scraper.ensure_logged_in(page, email, password):
                        print(f"⚠️ Втрачено сесію для {email}, спробуємо перелогінитись")
                        if not await scraper.login(page, email, password):
                            print(f"❌ Не вдалося перелогінитись для {email}")
                            break
                        await scraper.save_context(context, email)

            except Exception as e:
                print(f"🔴 Критична помилка для {email}: {str(e)[:100]}...")
                await browser.close()

    # Запускаємо обробку всіх акаунтів паралельно
    await asyncio.gather(
        *[process_account(user_id, email, password) for user_id, email, password in all_users],
        return_exceptions=True
    )

if __name__ == "__main__":
    asyncio.run(main()) 