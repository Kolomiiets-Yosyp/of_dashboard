import asyncio
import time

from playwright.async_api import async_playwright
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from typing import Set, Tuple, List

UKR_MONTHS = {
    'січ': 1, 'лют': 2, 'бер': 3, 'квіт': 4, 'трав': 5, 'черв': 6,
    'лип': 7, 'сер': 8, 'вер': 9, 'жов': 10, 'лис': 11, 'гру': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

# === Клас для роботи з БД ===
class NotificationTracker:
    def __init__(self):
        self.db_path = 'onlyfans_notifications.db'
        self.processed_notifications: Set[Tuple[str, str, str]] = set()
        self.db_lock = Lock()
        self.init_db()

    def init_db(self):
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    post_text TEXT NOT NULL,
                    tag_username TEXT NOT NULL,
                    post_time TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            ''')
            conn.commit()
            conn.close()

    def get_all_users(self):
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

    def save_notification(self, user_id: int, notification_type: str, username: str, content: str, of_date_str: str) -> bool:
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
                ''', (user_id, notification_type, username, content, formatted_time, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                self.processed_notifications.add(notification_key)
                print(f"✅ Збережено: {notification_type} | {username} | {formatted_time}")
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()

    def save_post_statistics(self, user_id: int, date: str, post_count: int) -> bool:
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

    def save_tracking_link_stats(self, user_id: int, date: str, click_count: int) -> bool:
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

    def save_post_tag(self, user_id: int, post_text: str, tag_username: str, post_time: datetime):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO post_tags (user_id, post_text, tag_username, post_time, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, post_text, tag_username, post_time.strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            print(f"✅ Збережено тег: @{tag_username} | {post_time}")
        except sqlite3.Error as e:
            print(f"Помилка збереження тега: {e}")
        finally:
            conn.close()

    def parse_of_date(self, date_str: str) -> datetime:
        try:
            date_str = date_str.replace(',', '').strip()
            parts = date_str.split()
            if len(parts) < 2:
                return None
            # 🇺🇦 Український формат
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
            # 🇬🇧 Англійський формат
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
        thirty_days_ago = datetime.now() - timedelta(days=30)
        return date_obj >= thirty_days_ago

# === Клас для роботи з Playwright ===
class OnlyFansScraper:
    def __init__(self, tracker: NotificationTracker):
        self.tracker = tracker

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
            await page.goto("https://onlyfans.com/my/statistics/reach/tracking-links", timeout=60000)
            await asyncio.sleep(5)
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y-%m-%d')
            # Тут потрібно клікати календар і вибирати дату, як у Selenium-версії
            # Для спрощення: шукаємо перший елемент з класом .b-engagements-summary__item
            click_count_element = await page.query_selector('.b-engagements-summary__item')
            click_count = 0
            if click_count_element:
                text = await click_count_element.inner_text()
                try:
                    click_count = int(text.split()[0])
                except Exception:
                    click_count = 0
            self.tracker.save_tracking_link_stats(user_id, yesterday_str, click_count)
        except Exception as e:
            print(f"Помилка обробки сторінки трекінг-посилань: {e}")

    async def process_engagement_page(self, page, user_id: int):
        try:
            await page.goto("https://onlyfans.com/my/statistics/engagement/posts", timeout=60000)
            await asyncio.sleep(5)
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
            await page.goto("https://onlyfans.com/my/queue", timeout=60000)
            await asyncio.sleep(5)
            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')
            scheduled_posts = {}
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
            with self.tracker.db_lock:
                conn = sqlite3.connect(self.tracker.db_path)
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

    async def process_subscribed_notifications(self, page, user_id: int):
        """Обробляє сторінку підписок з точним контролем скролу та збором даних"""
        try:
            # 1. Ініціалізація
            await page.goto('https://onlyfans.com/my/notifications/subscribed', timeout=60000)
            await page.wait_for_selector('.b-notifications__list__item', timeout=15000)

            thirty_days_ago = (datetime.now() - timedelta(days=30)).date()
            oldest_date_in_view = datetime.now().date()
            scroll_attempts = 0
            max_scroll_attempts = 8
            processed_usernames = set()

            # 2. Головний цикл обробки
            while oldest_date_in_view > thirty_days_ago and scroll_attempts < max_scroll_attempts:
                # 2.1. Отримання поточних елементів
                notifications = await page.query_selector_all('.b-notifications__list__item')
                if not notifications:
                    break

                # 2.2. Визначення найстарішої дати
                current_oldest_date = datetime.now().date()
                date_elements = await page.query_selector_all('.g-date span[title]')

                for date_element in date_elements:
                    try:
                        date_str = await date_element.get_attribute('title')
                        notification_date = self.parse_of_date(date_str).date()
                        if notification_date < current_oldest_date:
                            current_oldest_date = notification_date
                    except:
                        continue

                oldest_date_in_view = current_oldest_date
                print(f"Найстаріша дата у видимому діапазоні: {oldest_date_in_view}")

                # 2.3. Обробка сповіщень
                for item in notifications:
                    try:
                        # Отримання даних
                        username_element = await item.query_selector('a[href*="/"]')
                        username = await username_element.evaluate(
                            'el => el.href.replace("https://onlyfans.com/", "").split("/")[0]')

                        if username in processed_usernames:
                            continue

                        time_element = await item.query_selector('.g-date span')
                        of_date_str = await time_element.get_attribute('title')
                        notification_date = self.parse_of_date(of_date_str)

                        # Збереження даних
                        self.tracker.add_notification(
                            user_id=user_id,
                            notification_type="subscribed",
                            content=f"{username} підписався {of_date_str}",
                            timestamp=notification_date
                        )
                        processed_usernames.add(username)

                    except Exception as e:
                        print(f"Помилка обробки сповіщення: {e}")

                # 2.4. Скрол та оновлення
                await page.evaluate('window.scrollBy(0, document.documentElement.clientHeight)')
                await asyncio.sleep(3)  # Чекаємо на завантаження нового контенту

                scroll_attempts += 1
                if scroll_attempts % 5 == 0:
                    print(f"Скрол #{scroll_attempts}. Оброблено: {len(processed_usernames)}")

            print(f"Завершено. Остання дата: {oldest_date_in_view}. Усього підписок: {len(processed_usernames)}")
            return True

        except Exception as e:
            print(f"Критична помилка: {str(e)}")
            return False

    async def scrape_subscribed_notifications(self, page, user_id: int, notification_type: str, url: str, days_limit: int = 30):
        try:
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

    async with async_playwright() as p:
        # Налаштування браузера
        browser = await p.chromium.launch(headless=False, timeout=60000)

        async def login_tab(user_id, email, password):
            """Обробка логіну в окремій вкладці"""
            context = await browser.new_context()
            page = await context.new_page()
            try:
                if not await scraper.login(page, email, password):
                    print(f"⚠️ Помилка логіну: {email}")
                    return None
                return context
            except Exception as e:
                print(f"🚨 Помилка логіну {email}: {str(e)[:100]}...")
                await context.close()
                return None

        async def process_notifications(context, user_id):
            """Обробка сповіщень в окремій вкладці"""
            page = await context.new_page()
            try:
                await scraper.scrape_subscribed_notifications(page, user_id, "subscribed", "https://onlyfans.com/my/notifications/subscribed")
                await scraper.scrape_profile_posts(page, user_id)
            finally:
                await page.close()

        async def process_analytics(context, user_id):
            """Обробка аналітики в окремій вкладці"""
            page = await context.new_page()
            try:
                await scraper.process_tracking_links_page(page, user_id)
                await scraper.process_engagement_page(page, user_id)
                await scraper.process_queue_page(page, user_id)
                await scraper.scrape_subscribed_notifications(page, user_id, "tags", "https://onlyfans.com/my/notifications/tags")

            finally:
                await page.close()

        # Обробка користувачів
        for user_id, email, password in all_users:
            try:
                # 1. Вкладка логіну
                context = await login_tab(user_id, email, password)
                if not context:
                    continue

                # 2. Паралельна обробка в окремих вкладках
                await asyncio.gather(
                    process_notifications(context, user_id),
                    process_analytics(context, user_id),
                    return_exceptions=True
                )

                print(f"✅ Успішно оброблено {email}")
            except Exception as e:
                print(f"🔴 Критична помилка для {email}: {str(e)[:100]}...")
            finally:
                await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 