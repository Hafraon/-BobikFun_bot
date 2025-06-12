import requests
import asyncio
import random
import logging
import json
import time
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from typing import Dict, List, Optional
import threading

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedBobikBot:
    def __init__(self):
        self.bot_token = "7882259321:AAGGqql6LD6bzLHTOb1HdKUYs2IJBZqsd6E"
        self.channel_id = "@BobikFun"
        
        # Статистика з історією постів
        self.stats = {
            'posts_today': 0,
            'total_posts': 0,
            'last_post_time': None,
            'successful_posts': 0,
            'failed_posts': 0,
            'best_engagement_time': None,
            'daily_stats': {},
            'posted_memes': set(),  # Для уникнення дублікатів
            'hourly_posts': {},     # Статистика по годинах
            'last_api_check': None  # Час останньої перевірки API
        }
        
        # Оптимальний розклад (UTC) - 11 постів/день
        self.posting_schedule = [
            "05:00",  # Рання пташка
            "07:00",  # Ранковий кофе ☕
            "09:00",  # Початок робочого дня 💼
            "11:30",  # Перед обідом
            "13:00",  # Обідня перерва 🍽️
            "15:00",  # Після обіду ⚡
            "17:00",  # Кінець робочого дня
            "19:00",  # Вечерня активність 🏠
            "21:00",  # Прайм-тайм 📺
            "22:30",  # Пізній вечір
            "23:45"   # Нічні сови 🦉
        ]
        
        self.scheduler_running = False
        
        # Розширені джерела мемів з різними API
        self.meme_sources = {
            'general': [
                "https://meme-api.herokuapp.com/gimme",
                "https://meme-api.com/gimme",
                "https://api.reddit.com/r/memes/hot.json?limit=50",
                "https://meme-api.herokuapp.com/gimme/memes",
                "https://meme-api.herokuapp.com/gimme/dankmemes"
            ],
            'wholesome': [
                "https://meme-api.herokuapp.com/gimme/wholesomememes",
                "https://meme-api.herokuapp.com/gimme/MadeMeSmile",
                "https://api.reddit.com/r/wholesomememes/hot.json?limit=30"
            ],
            'tech': [
                "https://meme-api.herokuapp.com/gimme/ProgrammerHumor",
                "https://meme-api.herokuapp.com/gimme/softwaregore",
                "https://api.reddit.com/r/ProgrammerHumor/hot.json?limit=30"
            ],
            'relatable': [
                "https://meme-api.herokuapp.com/gimme/me_irl",
                "https://meme-api.herokuapp.com/gimme/meirl",
                "https://api.reddit.com/r/me_irl/hot.json?limit=30"
            ],
            'backup': [
                "https://official-joke-api.appspot.com/random_joke",
                "https://api.chucknorris.io/jokes/random"
            ]
        }
        
        # Якісні українські підписи за часом дня
        self.time_based_captions = {
            'morning': [
                "🌅 Коли прокинувся і зрозумів, що сьогодні не вихідний:",
                "☕ Ранкова кава і мем - єдине що тримає на плаву",
                "🐕 Поки ти спав, Бобік готував щось смішне",
                "🌞 Ранок понеділка vs твій настрій:",
                "😴 Будильник о 7 ранку - це злочин проти людяності"
            ],
            'work': [
                "💻 Коли бос питає про дедлайн, а ти ще не починав:",
                "📱 Перерва на мем серед робочого хаосу",
                "🤔 Коли робиш вигляд, що працюєш:",
                "💼 Робочі будні vs реальність:",
                "⌨️ Код-рев'ю vs мої очікування:",
                "📧 Коли в п'ятницю надходить 'терміновий' проект:"
            ],
            'lunch': [
                "🍔 Обідня перерва - священний час кожного працівника",
                "🥪 Коли їси і дивишся меми одночасно",
                "😋 Їжа смачніша під мемчики від Бобіка",
                "🍕 Обід в офісі vs обід вдома:",
                "🥗 Дієта vs те, що насправді їм:"
            ],
            'evening': [
                "🏠 Нарешті дома! Час для якісних мемів",
                "🛋️ Після роботи тільки диван і мемаси",
                "📺 Коли вибираєш між серіалом і мемами:",
                "🌆 Кінець робочого дня - почалося життя",
                "🎮 Коли планував продуктивний вечір:",
                "🍿 Ідеальний вечір: мемчики + щось смачне"
            ],
            'night': [
                "🌙 О 23:00: 'Ще один мемчик і спати'",
                "🦉 Нічний скрол мемів - моя суперсила",
                "📱 Коли мав лягти спати 2 години тому:",
                "⭐ Нічний Telegram серфінг в дії",
                "😅 Завтра рано вставати, але мемчики важливіше",
                "🌃 Коли всі сплять, а ти дивишся меми:"
            ]
        }
        
        # Релевантні українські хештеги
        self.trending_hashtags = [
            "#мемчик", "#гумор", "#релейтабл", "#настрій", 
            "#життя", "#робота", "#понеділок", "#кава",
            "#україна", "#бобік", "#смішно", "#мемас",
            "#офісlife", "#студентlife", "#дорослеlife"
        ]
        
    def create_main_menu(self) -> InlineKeyboardMarkup:
        """Створює головне меню бота"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Аналітика", callback_data="analytics"),
                InlineKeyboardButton("🧪 Тест пост", callback_data="test_post")
            ],
            [
                InlineKeyboardButton("🎲 Випадковий мем", callback_data="random_meme"),
                InlineKeyboardButton("📅 Розклад", callback_data="schedule")
            ],
            [
                InlineKeyboardButton("⚙️ Управління", callback_data="management"),
                InlineKeyboardButton("📈 Статус", callback_data="status")
            ],
            [
                InlineKeyboardButton("🔧 Налаштування", callback_data="settings"),
                InlineKeyboardButton("ℹ️ Допомога", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_management_menu(self) -> InlineKeyboardMarkup:
        """Меню управління ботом"""
        status_text = "🟢 Зупинити" if self.scheduler_running else "🔴 Запустити"
        callback_data = "stop_scheduler" if self.scheduler_running else "start_scheduler"
        
        keyboard = [
            [
                InlineKeyboardButton(f"{status_text} розклад", callback_data=callback_data),
                InlineKeyboardButton("🔄 Перезапустити", callback_data="restart_scheduler")
            ],
            [
                InlineKeyboardButton("🚀 Опублікувати ЗАРАЗ", callback_data="post_now"),
                InlineKeyboardButton("🧹 Очистити статистику", callback_data="clear_stats")
            ],
            [
                InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_analytics_menu(self) -> InlineKeyboardMarkup:
        """Меню аналітики"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Загальна статистика", callback_data="general_stats"),
                InlineKeyboardButton("⏰ По годинах", callback_data="hourly_stats")
            ],
            [
                InlineKeyboardButton("📈 Успішність", callback_data="success_rate"),
                InlineKeyboardButton("🎯 Топ години", callback_data="best_hours")
            ],
            [
                InlineKeyboardButton("📋 Експорт даних", callback_data="export_data"),
                InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_permanent_menu(self) -> ReplyKeyboardMarkup:
        """Створює постійне меню внизу екрану"""
        keyboard = [
            ["📊 Аналітика", "🧪 Тест пост"],
            ["🎲 Мем", "📅 Розклад"], 
            ["⚙️ Управління", "📈 Статус"],
            ["🔧 Налаштування", "ℹ️ Допомога"]
        ]
        return ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True,        # Автоматично підбирає розмір
            one_time_keyboard=False,     # Не зникає після використання
            selective=False,             # Для всіх користувачів
            input_field_placeholder="Обери дію з меню 👇"  # Підказка в полі вводу
        )
    
    def create_settings_menu(self) -> InlineKeyboardMarkup:
        """Меню налаштувань"""
        keyboard = [
            [
                InlineKeyboardButton("🎨 Стиль підписів", callback_data="caption_style"),
                InlineKeyboardButton("🔍 Джерела мемів", callback_data="meme_sources")
            ],
            [
                InlineKeyboardButton("⏰ Змінити розклад", callback_data="modify_schedule"),
                InlineKeyboardButton("🏷️ Хештеги", callback_data="hashtags")
            ],
            [
                InlineKeyboardButton("🔄 Скинути налаштування", callback_data="reset_settings"),
                InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_time_category(self, hour: int) -> str:
        """Визначає категорію часу для підбору підписів"""
        if 5 <= hour < 10:
            return 'morning'
        elif 10 <= hour < 14:
            return 'work'
        elif 14 <= hour < 17:
            return 'lunch'
        elif 17 <= hour < 22:
            return 'evening'
        else:
            return 'night'

    def get_meme_advanced(self) -> Optional[Dict]:
        """Розширений пошук мемів з ротацією джерел та уникненням дублікатів"""
        max_attempts = 50  # Максимум спроб знайти унікальний мем
        attempts = 0
        
        # Отримуємо всі джерела та перемішуємо для різноманітності
        all_sources = []
        for category, urls in self.meme_sources.items():
            if category != 'backup':  # Backup використовуємо в крайньому випадку
                all_sources.extend([(url, category) for url in urls])
        
        random.shuffle(all_sources)
        
        while attempts < max_attempts:
            for api_url, category in all_sources:
                try:
                    if 'reddit.com' in api_url:
                        # Обробка Reddit API
                        meme = self.get_reddit_meme(api_url)
                    elif 'joke-api' in api_url or 'chucknorris' in api_url:
                        # Бекап джерела - жарти
                        meme = self.get_joke_as_meme(api_url)
                    else:
                        # Стандартні мем API
                        meme = self.get_standard_meme(api_url)
                    
                    if meme and self.is_unique_meme(meme):
                        # Додаємо до історії постів
                        self.stats['posted_memes'].add(meme.get('url', ''))
                        
                        # Очищуємо історію якщо забагато
                        if len(self.stats['posted_memes']) > 1000:
                            # Залишаємо тільки останні 500
                            self.stats['posted_memes'] = set(list(self.stats['posted_memes'])[-500:])
                        
                        logger.info(f"✅ Знайдено унікальний мем з {category}: {api_url}")
                        return meme
                        
                except Exception as e:
                    logger.error(f"Помилка API {api_url}: {e}")
                    continue
            
            attempts += 1
            logger.warning(f"Спроба {attempts}: не знайдено унікальних мемів")
        
        # Якщо не знайшли унікальний - використовуємо fallback
        logger.warning("Використовую fallback мем")
        return self.get_fallback_meme()

    def get_standard_meme(self, api_url: str) -> Optional[Dict]:
        """Отримує мем зі стандартного API"""
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if self.is_quality_meme_advanced(data):
                return {
                    'url': data.get('url'),
                    'title': data.get('title', ''),
                    'ups': data.get('ups', 0),
                    'subreddit': data.get('subreddit', ''),
                    'source_api': api_url
                }
        return None

    def get_reddit_meme(self, api_url: str) -> Optional[Dict]:
        """Отримує мем з Reddit API"""
        headers = {'User-Agent': 'BobikBot/1.0'}
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            posts = data.get('data', {}).get('children', [])
            
            # Фільтруємо якісні пости
            for post in posts:
                post_data = post.get('data', {})
                if self.is_quality_reddit_post(post_data):
                    return {
                        'url': post_data.get('url'),
                        'title': post_data.get('title', ''),
                        'ups': post_data.get('ups', 0),
                        'subreddit': post_data.get('subreddit', ''),
                        'source_api': api_url
                    }
        return None

    def get_joke_as_meme(self, api_url: str) -> Optional[Dict]:
        """Перетворює жарт на мем (backup джерело)"""
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'joke-api' in api_url:
                    joke_text = f"{data.get('setup', '')}\n{data.get('punchline', '')}"
                elif 'chucknorris' in api_url:
                    joke_text = data.get('value', '')
                
                return {
                    'url': 'https://i.imgflip.com/1bij.jpg',  # Стандартне зображення для жартів
                    'title': joke_text[:200] + '...' if len(joke_text) > 200 else joke_text,
                    'ups': 500,  # Середній рейтинг
                    'subreddit': 'jokes',
                    'source_api': api_url
                }
        except Exception as e:
            logger.error(f"Помилка отримання жарту: {e}")
        return None

    def is_quality_reddit_post(self, post_data: Dict) -> bool:
        """Перевіряє якість Reddit поста"""
        try:
            url = post_data.get('url', '')
            title = post_data.get('title', '').lower()
            ups = post_data.get('ups', 0)
            
            # Перевірка формату
            if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                return False
            
            # Мінімальний рейтинг
            if ups < 50:
                return False
            
            # Фільтр неприйнятного контенту
            bad_words = ['nsfw', 'porn', 'sex', 'politics']
            if any(word in title for word in bad_words):
                return False
            
            return True
            
        except Exception:
            return False

    def is_unique_meme(self, meme_data: Dict) -> bool:
        """Перевіряє чи мем унікальний (не публікувався раніше)"""
        if not meme_data:
            return False
        
        meme_url = meme_data.get('url', '')
        meme_title = meme_data.get('title', '')
        
        # Перевіряємо URL
        if meme_url in self.stats['posted_memes']:
            return False
        
        # Перевіряємо схожість назв (базова перевірка)
        for posted_url in list(self.stats['posted_memes'])[-100:]:  # Перевіряємо останні 100
            if posted_url and abs(len(meme_title) - len(posted_url)) < 10:
                if any(word in meme_title.lower() for word in posted_url.lower().split() if len(word) > 3):
                    return False
        
        return True

    def is_quality_meme_advanced(self, data: Dict) -> bool:
        """Покращена фільтрація якості мемів"""
        try:
            url = data.get('url', '')
            title = data.get('title', '').lower()
            ups = data.get('ups', 0)
            
            # Перевірка формату
            if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                return False
            
            # Фільтр неприйнятного контенту
            bad_words = ['nsfw', 'porn', 'sex', 'nude', 'politics', 'trump', 'biden']
            if any(word in title for word in bad_words):
                return False
            
            # Адаптивний поріг якості
            current_hour = datetime.now().hour
            
            # В пікові години (ранок, обід, вечір) - вищі вимоги
            if current_hour in [7, 8, 9, 12, 13, 18, 19, 20]:
                return ups >= 100
            else:
                return ups >= 50
                
        except Exception:
            return False

    def get_fallback_meme(self) -> Dict:
        """Резервні меми коли API не працюють"""
        fallback_memes = [
            {
                'url': 'https://i.imgflip.com/1bij.jpg',
                'title': 'Success Kid - коли все йде за планом!',
                'ups': 9999,
                'subreddit': 'fallback'
            },
            {
                'url': 'https://i.imgflip.com/30b1gx.jpg', 
                'title': 'Drake pointing - правильний вибір!',
                'ups': 8888,
                'subreddit': 'fallback'
            },
            {
                'url': 'https://i.imgflip.com/1otk96.jpg',
                'title': 'Distracted Boyfriend - коли є вибір!',
                'ups': 7777,
                'subreddit': 'fallback'
            }
        ]
        
        return random.choice(fallback_memes)

    def generate_smart_caption(self, meme_data: Dict) -> str:
        """Генерує розумні підписи залежно від часу та контенту"""
        current_hour = datetime.now().hour
        time_category = self.get_time_category(current_hour)
        
        # Вибираємо підпис за часом дня
        time_caption = random.choice(self.time_based_captions[time_category])
        
        # Обробляємо назву мему - прибираємо англійські назви
        title = meme_data.get('title', '')
        
        # Фільтруємо англійські мемні назви і замінюємо на зрозумілі
        meme_translations = {
            'Drake': '🎵 Той момент коли вибираєш:',
            'Distracted Boyfriend': '👀 Коли з\'явилася альтернатива:',
            'Woman Yelling at Cat': '😾 Конфлікт інтересів:',
            'Success Kid': '💪 Коли все йде за планом:',
            'Expanding Brain': '🧠 Еволюція думок:',
            'Change My Mind': '🤔 Спробуй переконати:',
            'This is Fine': '🔥 Все під контролем:',
            'Surprised Pikachu': '😲 Коли очевидне стає несподіванкою:',
            'Hide the Pain Harold': '😅 Коли робиш вигляд що все ок:'
        }
        
        # Перевіряємо чи є відома англійська назва мему
        processed_title = title
        for eng_name, ukr_replacement in meme_translations.items():
            if eng_name.lower() in title.lower():
                processed_title = ukr_replacement
                break
        else:
            # Якщо немає відомої назви - перевіряємо чи назва англійська
            if any(word in title.lower() for word in ['meme', 'when', 'you', 'me', 'the', 'and', 'with', 'that']):
                # Якщо назва англійська - замінюємо на загальну фразу
                general_phrases = [
                    "😂 Ситуація знайома?",
                    "🎯 В точку!",
                    "😄 Це про всіх нас",
                    "💯 Релейтабл контент",
                    "🤝 Хто теж так робить?",
                    "😅 Життєва ситуація",
                    "🎪 Цирк в нашому житті"
                ]
                processed_title = random.choice(general_phrases)
            # Якщо назва не англійська - залишаємо як є, але скорочуємо
            elif len(title) > 100:
                processed_title = title[:97] + "..."
        
        # Генеруємо хештеги
        hashtags = random.sample(self.trending_hashtags, 2)
        hashtag_str = ' '.join(hashtags)
        
        # Формуємо фінальний підпис
        if processed_title and processed_title != title:
            # Якщо ми переклали назву мему
            caption = f"{time_caption}\n\n{processed_title}\n\n{hashtag_str}"
        else:
            # Якщо залишили оригінальну назву
            caption = f"{time_caption}\n\n💭 {processed_title}\n\n{hashtag_str}"
        
        return caption

    async def post_meme_to_channel_advanced(self) -> bool:
        """Покращена публікація з аналітикою та уникненням дублікатів"""
        try:
            meme = self.get_meme_advanced()
            if not meme:
                logger.error("Не вдалося отримати унікальний мем")
                self.stats['failed_posts'] += 1
                return False
            
            caption = self.generate_smart_caption(meme)
            bot = Bot(token=self.bot_token)
            
            # Публікуємо мем
            result = await bot.send_photo(
                chat_id=self.channel_id,
                photo=meme['url'],
                caption=caption
            )
            
            # Оновлюємо розширену статистику
            current_time = datetime.now()
            self.stats['posts_today'] += 1
            self.stats['total_posts'] += 1
            self.stats['successful_posts'] += 1
            self.stats['last_post_time'] = current_time
            
            # Статистика по годинах
            hour_key = current_time.strftime('%H')
            if hour_key not in self.stats['daily_stats']:
                self.stats['daily_stats'][hour_key] = 0
            self.stats['daily_stats'][hour_key] += 1
            
            # Детальна статистика по годинах
            if hour_key not in self.stats['hourly_posts']:
                self.stats['hourly_posts'][hour_key] = []
            self.stats['hourly_posts'][hour_key].append({
                'time': current_time.isoformat(),
                'meme_title': meme.get('title', ''),
                'source': meme.get('source_api', ''),
                'message_id': result.message_id
            })
            
            logger.info(f"✅ Мем опубліковано! ID: {result.message_id}, Час: {current_time.strftime('%H:%M')}, Джерело: {meme.get('source_api', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка публікації: {e}")
            self.stats['failed_posts'] += 1
            return False

    def should_post_now(self) -> bool:
        """Перевіряє чи треба публікувати зараз"""
        current_time = datetime.now().strftime('%H:%M')
        return current_time in self.posting_schedule

    async def scheduler_loop(self):
        """Основний цикл планувальника"""
        logger.info("🕐 Планувальник запущений!")
        
        while self.scheduler_running:
            try:
                if self.should_post_now():
                    logger.info(f"⏰ Час публікації: {datetime.now().strftime('%H:%M')}")
                    await self.post_meme_to_channel_advanced()
                    
                    # Чекаємо 70 секунд щоб не повторювати в ту ж хвилину
                    await asyncio.sleep(70)
                else:
                    # Перевіряємо кожні 30 секунд
                    await asyncio.sleep(30)
                    
            except Exception as e:
                logger.error(f"Помилка в планувальнику: {e}")
                await asyncio.sleep(60)

    def start_scheduler(self):
        """Запуск планувальника в окремому потоці"""
        if not self.scheduler_running:
            self.scheduler_running = True
            
            def run_scheduler():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.scheduler_loop())
            
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("📅 Автоматичний розклад активовано!")

    def stop_scheduler(self):
        """Зупинка планувальника"""
        self.scheduler_running = False
        logger.info("⏹️ Планувальник зупинено!")

    async def button_callback(self, update, context):
        """Обробник натискань кнопок меню"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "main_menu":
            await query.edit_message_text(
                "🐕 **Головне меню Бобіка**\n\nОберіть дію:",
                reply_markup=self.create_main_menu(),
                parse_mode='Markdown'
            )
            
        elif data == "analytics":
            await query.edit_message_text(
                "📊 **Аналітика каналу**\n\nОберіть тип статистики:",
                reply_markup=self.create_analytics_menu(),
                parse_mode='Markdown'
            )
            
        elif data == "management":
            status = "🟢 Активний" if self.scheduler_running else "🔴 Зупинений"
            await query.edit_message_text(
                f"⚙️ **Управління ботом**\n\nПоточний статус: {status}\n\nОберіть дію:",
                reply_markup=self.create_management_menu(),
                parse_mode='Markdown'
            )
            
        elif data == "settings":
            await query.edit_message_text(
                "🔧 **Налаштування бота**\n\nОберіть що хочете налаштувати:",
                reply_markup=self.create_settings_menu(),
                parse_mode='Markdown'
            )
            
        elif data == "test_post":
            await query.edit_message_text("🧪 Публікую тестовий мем...")
            success = await self.post_meme_to_channel_advanced()
            
            if success:
                text = "✅ **Тестовий мем успішно опубліковано!**\n\nПеревірте канал @BobikFun"
            else:
                text = "❌ **Помилка публікації**\n\nПеревірте налаштування бота"
                
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )
            
        elif data == "random_meme":
            await query.edit_message_text("🔍 Шукаю найкращий мем...")
            
            meme = self.get_meme_advanced()
            if meme:
                caption = self.generate_smart_caption(meme)
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=meme['url'],
                    caption=caption
                )
                await query.edit_message_text(
                    "✅ **Мем відправлено!**",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Ще один мем", callback_data="random_meme"), InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **Не вдалося знайти мем**\n\nСпробуйте ще раз",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Спробувати ще", callback_data="random_meme"), InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                    parse_mode='Markdown'
                )
                
        elif data == "schedule":
            schedule_text = self.get_schedule_info()
            await query.edit_message_text(
                schedule_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )
            
        elif data == "status":
            status_text = self.get_detailed_status()
            await query.edit_message_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Оновити", callback_data="status"), InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )
            
        elif data == "general_stats":
            stats_text = self.get_analytics()
            await query.edit_message_text(
                stats_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="analytics")]]),
                parse_mode='Markdown'
            )
            
        elif data == "hourly_stats":
            hourly_text = self.get_hourly_analytics()
            await query.edit_message_text(
                hourly_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="analytics")]]),
                parse_mode='Markdown'
            )
            
        elif data == "success_rate":
            success_text = self.get_success_analytics()
            await query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="analytics")]]),
                parse_mode='Markdown'
            )
            
        elif data == "best_hours":
            best_hours_text = self.get_best_hours_analytics()
            await query.edit_message_text(
                best_hours_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="analytics")]]),
                parse_mode='Markdown'
            )
            
        elif data == "export_data":
            export_text = self.export_analytics_data()
            await query.edit_message_text(
                export_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="analytics")]]),
                parse_mode='Markdown'
            )
            
        elif data == "caption_style":
            await query.edit_message_text(
                "🎨 **Стиль підписів:**\n\nПоточний стиль: Релейтабл український гумор\n\nДоступні стилі:\n• Життєві ситуації ✅\n• Робочий гумор\n• IT меми\n• Студентський гумор",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="settings")]]),
                parse_mode='Markdown'
            )
            
        elif data == "meme_sources":
            sources_text = self.get_sources_info()
            await query.edit_message_text(
                sources_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="settings")]]),
                parse_mode='Markdown'
            )
            
        elif data == "modify_schedule":
            schedule_text = self.get_schedule_settings()
            await query.edit_message_text(
                schedule_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="settings")]]),
                parse_mode='Markdown'
            )
            
        elif data == "hashtags":
            hashtag_text = self.get_hashtags_info()
            await query.edit_message_text(
                hashtag_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="settings")]]),
                parse_mode='Markdown'
            )
            
        elif data == "reset_settings":
            await query.edit_message_text(
                "🔄 **Скидання налаштувань**\n\n⚠️ Це скине всі персональні налаштування до заводських.\n\nПродовжити?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Так, скинути", callback_data="confirm_reset")],
                    [InlineKeyboardButton("❌ Скасувати", callback_data="settings")]
                ]),
                parse_mode='Markdown'
            )
            
        elif data == "confirm_reset":
            # Скидаємо налаштування
            self.reset_bot_settings()
            await query.edit_message_text(
                "✅ **Налаштування скинуто!**\n\nВсі параметри повернуто до заводських значень.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="settings")]]),
                parse_mode='Markdown'
            )
            
        elif data == "start_scheduler":
            self.start_scheduler()
            await query.edit_message_text(
                "✅ **Автоматичний розклад запущено!**\n\nБот почне публікувати меми згідно розкладу",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="management")]]),
                parse_mode='Markdown'
            )
            
        elif data == "stop_scheduler":
            self.stop_scheduler()
            await query.edit_message_text(
                "⏹️ **Автоматичний розклад зупинено**\n\nМеми більше не публікуватимуться автоматично",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="management")]]),
                parse_mode='Markdown'
            )
            
        elif data == "post_now":
            await query.edit_message_text("🚀 Публікую мем ПРЯМО ЗАРАЗ...")
            success = await self.post_meme_to_channel_advanced()
            
            if success:
                text = "🎯 **Мем опубліковано поза розкладом!**\n\nПеревірте канал @BobikFun"
            else:
                text = "❌ **Помилка екстреної публікації**"
                
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Ще один ЗАРАЗ", callback_data="post_now"), InlineKeyboardButton("⬅️ Назад", callback_data="management")]]),
                parse_mode='Markdown'
            )
            
        elif data == "clear_stats":
            self.stats = {
                'posts_today': 0,
                'total_posts': 0,
                'last_post_time': None,
                'successful_posts': 0,
                'failed_posts': 0,
                'best_engagement_time': None,
                'daily_stats': {},
                'posted_memes': set(),
                'hourly_posts': {},
                'last_api_check': None
            }
            await query.edit_message_text(
                "🧹 **Статистику очищено!**\n\nВсі дані скинуто до початкових значень",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="management")]]),
                parse_mode='Markdown'
            )
            
        elif data == "help":
            help_text = self.get_help_info()
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )

    def get_schedule_info(self) -> str:
        """Детальна інформація про розклад"""
        current_time = datetime.now()
        next_post_times = []
        
        for time_str in self.posting_schedule:
            hour, minute = map(int, time_str.split(':'))
            post_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if post_time <= current_time:
                post_time += timedelta(days=1)
            next_post_times.append((time_str, post_time))
        
        next_post_time_str, next_post = min(next_post_times, key=lambda x: x[1])
        time_until_next = next_post - current_time
        
        schedule_text = f"""
⏰ **Розклад автопублікацій (UTC):**

🌅 **Ранок:**
• 05:00 - Рання пташка
• 07:00 - Ранкова кава ☕
• 09:00 - Початок робочого дня 💼

🌞 **День:**
• 11:30 - Перед обідом  
• 13:00 - Обідня перерва 🍽️
• 15:00 - Після обіду ⚡
• 17:00 - Кінець робочого дня

🌆 **Вечір:**
• 19:00 - Вечерня активність 🏠
• 21:00 - Прайм-тайм 📺
• 22:30 - Пізній вечір
• 23:45 - Нічні сови 🦉

📊 **Статистика:**
• Всього: {len(self.posting_schedule)} постів/день
• Статус: {'🟢 Активний' if self.scheduler_running else '🔴 Вимкнений'}
• Наступний пост: {next_post_time_str} (через {str(time_until_next).split('.')[0]})
"""
        return schedule_text

    def get_detailed_status(self) -> str:
        """Детальний статус бота"""
        current_time = datetime.now()
        
        # Прогрес дня
        completed_today = self.stats['posts_today']
        total_planned = len(self.posting_schedule)
        progress = (completed_today / total_planned) * 100 if total_planned > 0 else 0
        
        status_text = f"""
🤖 **Детальний статус Бобіка:**

⏰ **Час:**
• Зараз: {current_time.strftime('%H:%M:%S UTC')}
• Дата: {current_time.strftime('%d.%m.%Y')}

📊 **Прогрес дня:**
• Опубліковано: {completed_today}/{total_planned}
• Прогрес: {progress:.1f}%
• {'🎯 День завершено!' if completed_today >= total_planned else f'📝 Залишилось: {total_planned - completed_today}'}

🔄 **Статус систем:**
• Планувальник: {'🟢 Працює' if self.scheduler_running else '🔴 Зупинений'}
• API мемів: {'🟢 Доступно' if self.test_meme_api() else '🔴 Проблеми'}
• Канал: 🟢 Підключено

🎯 **Успішність:**
• Успішних постів: {self.stats['successful_posts']}
• Невдалих постів: {self.stats['failed_posts']}
• Успішність: {(self.stats['successful_posts']/(max(1, self.stats['successful_posts'] + self.stats['failed_posts']))*100):.1f}%
"""
        return status_text

    def test_meme_api(self) -> bool:
        """Швидкий тест доступності API"""
        try:
            response = requests.get("https://meme-api.herokuapp.com/gimme", timeout=5)
            return response.status_code == 200
        except:
            return False

    async def handle_permanent_menu(self, update, context):
        """Обробник постійного меню"""
        text = update.message.text
        logger.info(f"Натиснуто кнопку: {text}")
        
        if text == "📊 Аналітика":
            await update.message.reply_text(
                "📊 **Аналітика каналу**\n\nОберіть тип статистики:",
                reply_markup=self.create_analytics_menu(),
                parse_mode='Markdown'
            )
            
        elif text == "🧪 Тест пост":
            await update.message.reply_text("🧪 Публікую тестовий мем...")
            success = await self.post_meme_to_channel_advanced()
            
            if success:
                await update.message.reply_text(
                    "✅ **Тестовий мем успішно опубліковано!**\n\nПеревірте канал @BobikFun",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ **Помилка публікації**")
                
        elif text == "🎲 Мем":
            await update.message.reply_text("🔍 Шукаю найкращий мем...")
            
            meme = self.get_meme_advanced()
            if meme:
                caption = self.generate_smart_caption(meme)
                await update.message.reply_photo(photo=meme['url'], caption=caption)
            else:
                await update.message.reply_text("😔 Не знайшов мему, спробуй ще раз!")
                
        elif text == "📅 Розклад":
            schedule_text = self.get_schedule_info()
            await update.message.reply_text(
                schedule_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Управління", callback_data="management")]]),
                parse_mode='Markdown'
            )
            
        elif text == "⚙️ Управління":
            status = "🟢 Активний" if self.scheduler_running else "🔴 Зупинений"
            await update.message.reply_text(
                f"⚙️ **Управління ботом**\n\nПоточний статус: {status}\n\nОберіть дію:",
                reply_markup=self.create_management_menu(),
                parse_mode='Markdown'
            )
            
        elif text == "📈 Статус":
            status_text = self.get_detailed_status()
            await update.message.reply_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Оновити", callback_data="status")]]),
                parse_mode='Markdown'
            )
            
        elif text == "🔧 Налаштування":
            await update.message.reply_text(
                "🔧 **Налаштування бота**\n\nОберіть що хочете налаштувати:",
                reply_markup=self.create_settings_menu(),
                parse_mode='Markdown'
            )
            
        elif text == "ℹ️ Допомога":
            help_text = self.get_help_info()
            await update.message.reply_text(
                help_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔧 Налаштування", callback_data="settings")]]),
                parse_mode='Markdown'
            )
        else:
            # Якщо текст не розпізнано, показуємо меню
            await update.message.reply_text(
                f"🤔 Не розумію команду '{text}'\n\nВикористовуй кнопки меню:",
                reply_markup=self.create_permanent_menu(),
                parse_mode='Markdown'
            )

    def get_hourly_analytics(self) -> str:
        """Аналітика по годинах"""
        if not self.stats['daily_stats']:
            return "📊 **Статистика по годинах:**\n\nДаних ще немає. Зачекайте кілька публікацій."
        
        # Сортуємо години по кількості постів
        sorted_hours = sorted(self.stats['daily_stats'].items(), key=lambda x: x[1], reverse=True)
        
        hourly_text = "📊 **Статистика по годинах:**\n\n"
        
        for hour, count in sorted_hours[:10]:  # Топ 10 годин
            percentage = (count / sum(self.stats['daily_stats'].values())) * 100
            hourly_text += f"• **{hour}:00** - {count} постів ({percentage:.1f}%)\n"
        
        # Додаємо рекомендації
        if sorted_hours:
            best_hour = sorted_hours[0][0]
            hourly_text += f"\n🎯 **Найактивніша година:** {best_hour}:00"
        
        return hourly_text

    def get_success_analytics(self) -> str:
        """Аналітика успішності"""
        total_attempts = self.stats['successful_posts'] + self.stats['failed_posts']
        
        if total_attempts == 0:
            return "📈 **Аналітика успішності:**\n\nДаних ще немає."
        
        success_rate = (self.stats['successful_posts'] / total_attempts) * 100
        
        success_text = f"""
📈 **Аналітика успішності:**

✅ **Успішні пости:** {self.stats['successful_posts']}
❌ **Невдалі пости:** {self.stats['failed_posts']}
📊 **Загальна успішність:** {success_rate:.1f}%

🎯 **Оцінка якості:**
"""
        
        if success_rate >= 95:
            success_text += "🟢 Відмінно! Бот працює ідеально."
        elif success_rate >= 85:
            success_text += "🟡 Добре. Є невеликі проблеми з API."
        elif success_rate >= 70:
            success_text += "🟠 Середньо. Потрібна оптимізація джерел."
        else:
            success_text += "🔴 Погано. Потрібна термінова діагностика."
        
        return success_text

    def get_best_hours_analytics(self) -> str:
        """Аналітика найкращих годин"""
        if not self.stats['daily_stats']:
            return "🎯 **Топ години для публікацій:**\n\nДаних ще немає."
        
        sorted_hours = sorted(self.stats['daily_stats'].items(), key=lambda x: x[1], reverse=True)
        
        best_hours_text = "🎯 **Топ години для публікацій:**\n\n"
        
        # Топ 5 годин
        for i, (hour, count) in enumerate(sorted_hours[:5], 1):
            best_hours_text += f"{i}. **{hour}:00** - {count} постів\n"
        
        # Рекомендації по часовим зонам
        best_hours_text += "\n📍 **Рекомендації:**\n"
        best_hours_text += "• Найкраща активність: 09:00-12:00, 18:00-21:00\n"
        best_hours_text += "• Найгірша активність: 02:00-05:00\n"
        best_hours_text += "• Оптимально для України: +2 години до UTC"
        
        return best_hours_text

    def export_analytics_data(self) -> str:
        """Експорт даних аналітики"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'total_posts': self.stats['total_posts'],
            'posts_today': self.stats['posts_today'],
            'success_rate': (self.stats['successful_posts'] / max(1, self.stats['successful_posts'] + self.stats['failed_posts'])) * 100,
            'hourly_stats': self.stats['daily_stats'],
            'posted_memes_count': len(self.stats['posted_memes']),
            'scheduler_status': self.scheduler_running
        }
        
        export_text = f"""
📋 **Експорт даних аналітики:**

```json
{json.dumps(export_data, indent=2, ensure_ascii=False)}
```

📊 **Формат:** JSON
📅 **Дата експорту:** {datetime.now().strftime('%d.%m.%Y %H:%M')}
💾 **Розмір даних:** {len(str(export_data))} символів

💡 **Використання:** Скопіюй дані для зовнішнього аналізу
"""
        return export_text

    def get_sources_info(self) -> str:
        """Інформація про джерела мемів"""
        total_sources = sum(len(urls) for urls in self.meme_sources.values())
        
        sources_text = f"""
🔍 **Джерела мемів:**

📊 **Загальна інформація:**
• Всього джерел: {total_sources}
• Категорій: {len(self.meme_sources)}
• Унікальних постів: {len(self.stats['posted_memes'])}

📂 **Категорії:**
"""
        
        for category, urls in self.meme_sources.items():
            category_names = {
                'general': '🎭 Загальні меми',
                'wholesome': '😊 Позитивні меми', 
                'tech': '💻 IT гумор',
                'relatable': '🤝 Релейтабл контент',
                'backup': '🔄 Резервні джерела'
            }
            
            sources_text += f"• {category_names.get(category, category)}: {len(urls)} джерел\n"
        
        # Статус API
        api_status = "🟢 Доступно" if self.test_meme_api() else "🔴 Проблеми"
        sources_text += f"\n🌐 **Статус API:** {api_status}"
        
        return sources_text

    def get_schedule_settings(self) -> str:
        """Налаштування розкладу"""
        schedule_text = f"""
⏰ **Налаштування розкладу:**

📅 **Поточний розклад:** {len(self.posting_schedule)} постів/день

🕐 **Часи публікацій (UTC):**
"""
        
        for i, time_str in enumerate(self.posting_schedule, 1):
            schedule_text += f"{i}. {time_str}\n"
        
        schedule_text += f"""

⚙️ **Параметри:**
• Статус: {'🟢 Активний' if self.scheduler_running else '🔴 Зупинений'}
• Перевірка: кожні 30 секунд
• Часова зона: UTC (Київ +2 години)

💡 **Примітка:** Для зміни розкладу потрібно оновити код
"""
        
        return schedule_text

    def get_hashtags_info(self) -> str:
        """Інформація про хештеги"""
        hashtags_text = f"""
🏷️ **Налаштування хештегів:**

📊 **Поточні хештеги:**
{' '.join(self.trending_hashtags)}

📂 **Категорії:**
• Загальні: #мемчик #гумор #релейтабл
• Життєві: #життя #робота #студентlife
• Українські: #україна #настрій
• Специфічні: #офісlife #дорослеlife

🎯 **Використання:**
• 2 випадкових хештеги на пост
• Ротація для різноманітності
• Адаптація під час дня

💡 **Для зміни хештегів потрібно оновити код**
"""
        
        return hashtags_text

    def reset_bot_settings(self):
        """Скидає налаштування бота"""
        # Очищуємо статистику
        self.stats = {
            'posts_today': 0,
            'total_posts': 0,
            'last_post_time': None,
            'successful_posts': 0,
            'failed_posts': 0,
            'best_engagement_time': None,
            'daily_stats': {},
            'posted_memes': set(),
            'hourly_posts': {},
            'last_api_check': None
        }
        
        logger.info("🔄 Налаштування бота скинуто до заводських")

    def get_help_info(self) -> str:
        """Інформація про допомогу"""
        return """
ℹ️ **Довідка по боту Бобік:**

🎯 **Основні функції:**
• Автоматична публікація 11 мемів/день
• Розумні українські підписи
• Аналітика та статистика
• Ручне управління публікаціями

📱 **Постійне меню (внизу екрану):**
• **📊 Аналітика** - статистика каналу
• **🧪 Тест пост** - швидка публікація
• **🎲 Мем** - випадковий мем приватно
• **📅 Розклад** - план публікацій
• **⚙️ Управління** - запуск/зупинка
• **📈 Статус** - поточний стан
• **🔧 Налаштування** - конфігурація
• **ℹ️ Допомога** - ця довідка

🎛️ **Команди:**
• `/menu` - показати постійне меню
• `/advanced` - розширене інлайн меню
• `/m` - швидке відновлення меню
• `/hide` - приховати постійне меню

⚙️ **Управління:**
• Запуск/зупинка розкладу
• Екстрена публікація
• Очищення статистики
• Налаштування параметрів

📊 **Аналітика:**
• Загальна статистика
• Статистика по часах
• Найкращі години для постів

❓ **Потрібна допомога?**
Звертайтесь до адміністратора каналу!
"""

    def get_analytics(self) -> str:
        """Генерує детальну аналітику"""
        success_rate = 0
        if self.stats['successful_posts'] + self.stats['failed_posts'] > 0:
            success_rate = (self.stats['successful_posts'] / 
                          (self.stats['successful_posts'] + self.stats['failed_posts']) * 100)
        
        # Знаходимо найактивнішу годину
        best_hour = "Немає даних"
        if self.stats['daily_stats']:
            best_hour_key = max(self.stats['daily_stats'], key=self.stats['daily_stats'].get)
            best_hour = f"{best_hour_key}:00"
        
        analytics = f"""
📊 **Розширена аналітика Бобіка:**

📈 **Основна статистика:**
• Постів сьогодні: {self.stats['posts_today']}
• Всього постів: {self.stats['total_posts']}
• Успішних: {self.stats['successful_posts']}
• Невдалих: {self.stats['failed_posts']}
• Успішність: {success_rate:.1f}%

⏰ **Часова аналітика:**
• Останній пост: {self.stats['last_post_time'] or 'Ще не було'}
• Найактивнішa година: {best_hour}
• Розклад: {len(self.posting_schedule)} публікацій/день

🎯 **Налаштування:**
• Джерел мемів: {sum(len(urls) for urls in self.meme_sources.values())}
• Автопланувальник: {'✅ Активний' if self.scheduler_running else '❌ Вимкнений'}
• Канал: @BobikFun
"""
        return analytics

    async def start_command(self, update, context):
        permanent_menu = self.create_permanent_menu()
        await update.message.reply_text(
            "🐕 **Привіт! Я покращений Бобік!**\n\n"
            "🚀 **Нові можливості:**\n"
            "• 11 автопостів на день\n"
            "• Розумні українські підписи\n"
            "• Постійне меню управління\n"
            "• Покращена аналітика\n"
            "• Множинні джерела мемів\n\n"
            "📱 **Постійне меню з'явилося внизу екрану!**\n"
            "Натискай кнопки замість введення команд.\n\n"
            "🔗 **Канал:** @BobikFun",
            reply_markup=permanent_menu,
            parse_mode='Markdown'
        )

    async def menu_command(self, update, context):
        """Команда для відновлення постійного меню"""
        permanent_menu = self.create_permanent_menu()
        await update.message.reply_text(
            "📱 **Постійне меню активовано!**\n\nВикористовуй кнопки внизу екрану:",
            reply_markup=permanent_menu,
            parse_mode='Markdown'
        )

    async def meme_command(self, update, context):
        await update.message.reply_text("🔍 Шукаю найкращий мем...")
        
        meme = self.get_meme_advanced()
        if meme:
            caption = self.generate_smart_caption(meme)
            await update.message.reply_photo(photo=meme['url'], caption=caption)
        else:
            await update.message.reply_text("😔 Не знайшов мему, спробуй ще раз!")

    async def test_command(self, update, context):
        await update.message.reply_text("🧪 Публікую тестовий мем...")
        
        success = await self.post_meme_to_channel_advanced()
        if success:
            await update.message.reply_text("✅ Тестовий мем опубліковано!")
        else:
            await update.message.reply_text("❌ Помилка публікації!")

    async def analytics_command(self, update, context):
        analytics_text = self.get_analytics()
        await update.message.reply_text(analytics_text, parse_mode='Markdown')

    async def schedule_command(self, update, context):
        schedule_text = f"""
⏰ **Розклад автопублікацій (UTC):**

🌅 **Ранок:**
• 05:00 - Рання пташка
• 07:00 - Ранкова кава ☕
• 09:00 - Початок робочого дня 💼

🌞 **День:**
• 11:30 - Перед обідом  
• 13:00 - Обідня перерва 🍽️
• 15:00 - Після обіду ⚡
• 17:00 - Кінець робочого дня

🌆 **Вечір:**
• 19:00 - Вечерня активність 🏠
• 21:00 - Прайм-тайм 📺
• 22:30 - Пізній вечір
• 23:45 - Нічні сови 🦉

📊 **Всього: {len(self.posting_schedule)} постів/день**
🔄 **Статус: {'✅ Активний' if self.scheduler_running else '❌ Вимкнений'}**
"""
        await update.message.reply_text(schedule_text, parse_mode='Markdown')

    async def status_command(self, update, context):
        current_time = datetime.now()
        next_post_times = []
        
        for time_str in self.posting_schedule:
            hour, minute = map(int, time_str.split(':'))
            post_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if post_time <= current_time:
                post_time += timedelta(days=1)
            next_post_times.append(post_time)
        
        next_post = min(next_post_times)
        time_until_next = next_post - current_time
        
        status_text = f"""
🤖 **Статус Бобіка:**

⏰ **Час зараз:** {current_time.strftime('%H:%M:%S UTC')}
⏭️ **Наступний пост:** {next_post.strftime('%H:%M')} 
⏳ **Через:** {str(time_until_next).split('.')[0]}

🔄 **Планувальник:** {'🟢 Працює' if self.scheduler_running else '🔴 Зупинений'}
📊 **Постів сьогодні:** {self.stats['posts_today']}/11
🎯 **Успішність:** {(self.stats['successful_posts']/(max(1, self.stats['successful_posts'] + self.stats['failed_posts']))*100):.1f}%
"""
        await update.message.reply_text(status_text, parse_mode='Markdown')

def main():
    """Головна функція з автоматичним розкладом та постійним меню"""
    bot = AdvancedBobikBot()
    
    # Створюємо додаток
    application = Application.builder().token(bot.bot_token).build()
    
    # Додаємо команди
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("menu", bot.menu_command)) 
    application.add_handler(CommandHandler("meme", bot.meme_command))
    application.add_handler(CommandHandler("test", bot.test_command))
    application.add_handler(CommandHandler("analytics", bot.analytics_command))
    application.add_handler(CommandHandler("schedule", bot.schedule_command))
    application.add_handler(CommandHandler("status", bot.status_command))
    
    # Швидка команда для відновлення меню
    async def restore_menu(update, context):
        await update.message.reply_text(
            "📱 **Постійне меню відновлено!**\n\nКнопки тепер внизу екрану:",
            reply_markup=bot.create_permanent_menu()
        )
    
    async def advanced_menu(update, context):
        """Показує розширене інлайн меню"""
        await update.message.reply_text(
            "🎛️ **Розширене меню:**\n\nДодаткові функції:",
            reply_markup=bot.create_main_menu(),
            parse_mode='Markdown'
        )
    
    async def hide_menu(update, context):
        """Приховує постійне меню"""
        await update.message.reply_text(
            "👻 **Постійне меню приховано**\n\n"
            "Для відновлення використовуй:\n"
            "• `/menu` - показати меню\n"
            "• `/m` - швидкий доступ",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    
    application.add_handler(CommandHandler("restore", restore_menu))
    application.add_handler(CommandHandler("m", restore_menu))  # Швидкий доступ
    application.add_handler(CommandHandler("advanced", advanced_menu))  # Розширене меню
    application.add_handler(CommandHandler("hide", hide_menu))  # Приховати меню
    
    # Додаємо обробник кнопок меню
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Додаємо обробник постійного меню
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.handle_permanent_menu
    ))
    
    # ЗАПУСКАЄМО АВТОМАТИЧНИЙ ПЛАНУВАЛЬНИК
    bot.start_scheduler()
    
    logger.info("🚀 Покращений Бобік з постійним меню запущений!")
    logger.info(f"📅 Буде публікувати {len(bot.posting_schedule)} мемів на день")
    logger.info("🎮 Постійне меню активовано!")
    
    # Запускаємо бота
    application.run_polling()

if __name__ == "__main__":
    main()
