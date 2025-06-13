import requests
import asyncio
import random
import logging
import json
import time
import hashlib
import os
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from typing import Dict, List, Optional
import threading

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Перевіряємо OpenAI доступність
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    logger.info("✅ OpenAI доступний")
except ImportError:
    OPENAI_AVAILABLE = False
    logger.info("⚠️ OpenAI не встановлено. Працюємо без AI локалізації.")

class AdvancedBobikBot:
    def __init__(self):
        # Основні налаштування
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "7882259321:AAGGqql6LD6bzLHTOb1HdKUYs2IJBZqsd6E")
        self.channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "@BobikFun")
        
        # OpenAI клієнт (якщо доступний)
        self.openai_client = None
        if OPENAI_AVAILABLE:
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key and openai_key.startswith('sk-'):
                try:
                    self.openai_client = OpenAI(api_key=openai_key)
                    logger.info("🤖 ChatGPT інтеграція активована")
                except Exception as e:
                    logger.error(f"Помилка ініціалізації OpenAI: {e}")
            else:
                logger.info("🔑 OPENAI_API_KEY не налаштовано. Працюємо без AI.")
        
        # Розширена статистика
        self.stats = {
            'posts_today': 0,
            'total_posts': 0,
            'last_post_time': None,
            'successful_posts': 0,
            'failed_posts': 0,
            'posted_hashes': set(),
            'localized_posts': 0,
            'api_failures': {},
            'content_sources': {}
        }
        
        # Оптимізований розклад для України (UTC+2 = Київський час)
        self.posting_schedule = [
            "03:00",  # 05:00 Київ - Рання пташка
            "05:00",  # 07:00 Київ - Ранкова кава
            "07:00",  # 09:00 Київ - Початок робочого дня
            "09:30",  # 11:30 Київ - Перед обідом
            "11:00",  # 13:00 Київ - Обідня перерва
            "13:00",  # 15:00 Київ - Після обіду
            "15:00",  # 17:00 Київ - Кінець робочого дня
            "17:00",  # 19:00 Київ - Вечерня активність
            "19:00",  # 21:00 Київ - Прайм-тайм
            "20:30",  # 22:30 Київ - Пізній вечір
            "21:45"   # 23:45 Київ - Нічні сови
        ]
        
        self.scheduler_running = False
        
        # Покращені джерела мемів з відмовостійкістю
        self.meme_sources = {
            'primary': {
                'reddit_memes': "https://api.reddit.com/r/memes/hot.json?limit=50",
                'reddit_dankmemes': "https://api.reddit.com/r/dankmemes/top.json?limit=50", 
                'reddit_wholesomememes': "https://api.reddit.com/r/wholesomememes/hot.json?limit=30"
            },
            'secondary': {
                'meme_api_1': "https://meme-api.herokuapp.com/gimme",
                'meme_api_2': "https://meme-api.com/gimme",
                'meme_api_3': "https://meme-api.herokuapp.com/gimme/memes"
            },
            'tech_specific': {
                'programmer_humor': "https://api.reddit.com/r/ProgrammerHumor/hot.json?limit=30",
                'meirl': "https://api.reddit.com/r/me_irl/hot.json?limit=30"
            },
            'backup': [
                "https://meme-api.herokuapp.com/gimme/dankmemes",
                "https://meme-api.herokuapp.com/gimme/wholesomememes"
            ]
        }
        
        # Українські контекстні підписи
        self.time_based_captions = {
            'early_morning': [
                "🌅 Ранні пташки, цей мем для вас!",
                "☕ Перша кава та свіжий мем - ідеальний ранок",
                "🐕 Бобік вже не спить, а ти?"
            ],
            'morning': [
                "🌅 Коли прокинувся і зрозумів, що сьогодні не вихідний:",
                "☕ Ранкова кава і мем - єдине що тримає на плаву",
                "💼 Початок робочого дня в стилі Бобіка"
            ],
            'work_hours': [
                "💻 Коли бос питає про прогрес, а ти дивився меми:",
                "📱 Офіційна перерва на мем серед робочого хаосу",
                "🤔 Коли робиш вигляд, що працюєш:"
            ],
            'lunch': [
                "🍔 Обідня перерва - священний час кожного працівника",
                "🥪 Коли їси і дивишся меми одночасно = мультитаскінг",
                "😋 Їжа смачніша під мемчики від Бобіка"
            ],
            'afternoon': [
                "⚡ Післяобідній енергетичний спад vs дедлайни:",
                "😴 15:00 - час коли продуктивність йде спати",
                "💼 Друга половина робочого дня like:"
            ],
            'evening': [
                "🏠 Нарешті дома! Час для якісних мемів",
                "🛋️ Після роботи тільки диван і мемаси",
                "📺 Коли вибираєш між серіалом і мемами:"
            ],
            'late_evening': [
                "🌃 Вечірній прайм-тайм мемів від Бобіка",
                "📱 Коли скролиш меми замість справ:",
                "🛋️ Вечірній чіл режим активовано"
            ],
            'night': [
                "🌙 О 23:00: 'Ще один мемчик і спати'",
                "🦉 Нічний скрол мемів - моя суперсила",
                "📱 Коли мав лягти спати 2 години тому:"
            ]
        }
        
        # Українські хештеги
        self.trending_hashtags = [
            "#мемчик", "#гумор", "#релейтабл", "#настрій", "#життя", 
            "#робота", "#айті", "#понеділок", "#кава", "#україна", 
            "#бобік", "#смішно", "#мемас", "#офісlife", "#студентlife"
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
                InlineKeyboardButton("📈 API Статус", callback_data="api_status")
            ],
            [
                InlineKeyboardButton("🤖 AI Статус", callback_data="ai_status"),
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

    def create_permanent_menu(self) -> ReplyKeyboardMarkup:
        """Створює постійне меню внизу екрану"""
        keyboard = [
            ["📊 Аналітика", "🧪 Тест пост"],
            ["🎲 Мем", "📅 Розклад"], 
            ["⚙️ Управління", "📈 API Статус"],
            ["🤖 AI Статус", "ℹ️ Допомога"]
        ]
        return ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Обери дію з меню 👇"
        )

    def get_time_category(self, hour: int) -> str:
        """Визначає категорію часу для підбору підписів (київський час)"""
        # Конвертуємо UTC в київський час (+2)
        kyiv_hour = (hour + 2) % 24
        
        if 5 <= kyiv_hour < 8:
            return 'early_morning'
        elif 8 <= kyiv_hour < 11:
            return 'morning'
        elif 11 <= kyiv_hour < 14:
            return 'work_hours'
        elif 14 <= kyiv_hour < 16:
            return 'lunch'
        elif 16 <= kyiv_hour < 18:
            return 'afternoon'
        elif 18 <= kyiv_hour < 21:
            return 'evening'
        elif 21 <= kyiv_hour < 24:
            return 'late_evening'
        else:
            return 'night'

    def test_meme_apis(self) -> Dict[str, bool]:
        """Тестує всі API джерела мемів"""
        api_status = {}
        
        # Тестуємо основні джерела
        for category, sources in self.meme_sources.items():
            if isinstance(sources, dict):
                for name, url in sources.items():
                    api_status[f"{category}_{name}"] = self._test_single_api(url)
            else:
                for i, url in enumerate(sources):
                    api_status[f"{category}_{i}"] = self._test_single_api(url)
        
        return api_status

    def _test_single_api(self, url: str) -> bool:
        """Тестує один API endpoint"""
        try:
            headers = {'User-Agent': 'BobikBot/2.0 (Ukrainian Meme Bot)'}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def get_meme_with_fallback(self) -> Optional[Dict]:
        """Отримує мем з системою fallback"""
        # Пробуємо по пріоритету
        source_priority = ['primary', 'tech_specific', 'secondary', 'backup']
        
        for category in source_priority:
            sources = self.meme_sources.get(category, {})
            
            if isinstance(sources, dict):
                items = sources.items()
            else:
                items = [(f"backup_{i}", url) for i, url in enumerate(sources)]
            
            for source_name, api_url in items:
                try:
                    meme = self.fetch_meme_from_api(api_url, source_name)
                    
                    if meme and self.is_quality_meme_ukraine(meme):
                        # Локалізуємо мем якщо є AI
                        if self.openai_client:
                            meme = self.localize_meme_with_ai(meme)
                            self.stats['localized_posts'] += 1
                        
                        # Оновлюємо статистику джерел
                        if source_name not in self.stats['content_sources']:
                            self.stats['content_sources'][source_name] = 0
                        self.stats['content_sources'][source_name] += 1
                        
                        logger.info(f"✅ Знайдено якісний мем з {source_name}")
                        return meme
                        
                except Exception as e:
                    # Записуємо статистику відмов
                    if source_name not in self.stats['api_failures']:
                        self.stats['api_failures'][source_name] = 0
                    self.stats['api_failures'][source_name] += 1
                    
                    logger.error(f"❌ Помилка {source_name}: {e}")
                    continue
        
        # Якщо всі API недоступні - використовуємо fallback
        logger.warning("🆘 Всі API недоступні, використовую fallback")
        return self.get_fallback_meme()

    def fetch_meme_from_api(self, api_url: str, source_name: str) -> Optional[Dict]:
        """Отримує мем з конкретного API"""
        headers = {'User-Agent': 'BobikBot/2.0 (Ukrainian Meme Bot)'}
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        # Обробляємо різні формати API
        if 'reddit.com' in api_url:
            return self.parse_reddit_response(data, source_name)
        else:
            return self.parse_meme_api_response(data, source_name)

    def parse_reddit_response(self, data: Dict, source: str) -> Optional[Dict]:
        """Парсить відповідь Reddit API"""
        try:
            posts = data.get('data', {}).get('children', [])
            
            # Фільтруємо найякісніші пости
            for post in posts:
                post_data = post.get('data', {})
                
                if self.is_valid_reddit_post(post_data):
                    return {
                        'url': post_data.get('url'),
                        'title': post_data.get('title', ''),
                        'score': post_data.get('score', 0),
                        'subreddit': post_data.get('subreddit', ''),
                        'source': source
                    }
        except Exception as e:
            logger.error(f"Reddit parse error: {e}")
        
        return None

    def parse_meme_api_response(self, data: Dict, source: str) -> Optional[Dict]:
        """Парсить відповідь meme-api"""
        try:
            if 'url' in data and 'title' in data:
                return {
                    'url': data.get('url'),
                    'title': data.get('title', 'Мем'),
                    'score': data.get('ups', 100),
                    'subreddit': data.get('subreddit', 'memes'),
                    'source': source
                }
        except Exception as e:
            logger.error(f"Meme API parse error: {e}")
        
        return None

    def is_valid_reddit_post(self, post_data: Dict) -> bool:
        """Перевіряє валідність Reddit поста"""
        try:
            url = post_data.get('url', '')
            title = post_data.get('title', '').lower()
            score = post_data.get('score', 0)
            
            # Перевірка формату зображення
            if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', 'i.redd.it', 'i.imgur.com']):
                return False
            
            # Мінімальний score
            if score < 50:
                return False
            
            # Фільтр неприйнятного контенту
            blacklist = ['nsfw', 'porn', 'sex', 'nude', 'politics']
            if any(word in title for word in blacklist):
                return False
            
            return True
        except Exception:
            return False

    def is_quality_meme_ukraine(self, meme_data: Dict) -> bool:
        """Перевіряє якість мему для української аудиторії"""
        if not meme_data:
            return False
            
        # Перевірка дублікатів по хешу
        meme_hash = self.generate_meme_hash(meme_data)
        if meme_hash in self.stats['posted_hashes']:
            return False
        
        # Перевірка релевантності для України
        if not self.is_relevant_for_ukraine(meme_data):
            return False
        
        # Додаємо до історії
        self.stats['posted_hashes'].add(meme_hash)
        
        # Очищуємо історію якщо забагато (залишаємо останні 1000)
        if len(self.stats['posted_hashes']) > 1000:
            old_hashes = list(self.stats['posted_hashes'])
            self.stats['posted_hashes'] = set(old_hashes[-500:])
        
        return True

    def generate_meme_hash(self, meme_data: Dict) -> str:
        """Генерує унікальний хеш для мему"""
        content = f"{meme_data.get('title', '')}{meme_data.get('url', '')}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def is_relevant_for_ukraine(self, meme_data: Dict) -> bool:
        """Перевіряє релевантність для української аудиторії"""
        title = meme_data.get('title', '').lower()
        
        # Blacklist для неактуальних тем
        ukraine_blacklist = [
            'thanksgiving', 'fourth of july', '4th of july', 'super bowl',
            'halloween costumes', 'american football', 'nfl', 'mlb'
        ]
        
        for term in ukraine_blacklist:
            if term in title:
                return False
        
        # Whitelist універсальних тем
        universal_topics = [
            'work', 'job', 'monday', 'coffee', 'weekend', 'sleep', 'food',
            'internet', 'phone', 'computer', 'programming', 'code', 'bug',
            'meeting', 'boss', 'salary', 'home', 'family', 'friends', 'meme'
        ]
        
        for topic in universal_topics:
            if topic in title:
                return True
        
        # Якщо високий score - ймовірно універсальний
        score = meme_data.get('score', 0)
        return score > 1000

    def localize_meme_with_ai(self, meme_data: Dict) -> Dict:
        """Локалізує мем за допомогою ChatGPT"""
        if not self.openai_client:
            return meme_data
            
        original_title = meme_data.get('title', '')
        
        # Перевіряємо чи потрібна локалізація
        if self.is_already_ukrainian(original_title):
            return meme_data
            
        try:
            prompt = f"""
            Адаптуй цю назву мему для української IT аудиторії 16-35 років:

            Оригінал: "{original_title}"

            Правила:
            - Переклади на українську якщо потрібно
            - Заміни американські реалії на українські аналоги
            - Зберігай гумор та суть
            - Використовуй сучасний український сленг
            - Максимум 120 символів
            - БЕЗ емодзі (вони будуть додані окремо)

            Українська назва:
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            
            localized_title = response.choices[0].message.content.strip()
            
            # Очищуємо від зайвих символів
            localized_title = localized_title.replace('"', '').replace('Українська назва:', '').strip()
            
            if localized_title and len(localized_title) > 10:
                meme_data['title'] = localized_title
                meme_data['localized'] = True
                logger.info(f"🇺🇦 Локалізовано: {original_title[:30]}... → {localized_title[:30]}...")
            
        except Exception as e:
            logger.error(f"🔴 Помилка локалізації AI: {e}")
            
        return meme_data

    def is_already_ukrainian(self, text: str) -> bool:
        """Перевіряє чи текст вже українською"""
        ukrainian_chars = 'абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'
        text_lower = text.lower()
        
        ukrainian_char_count = sum(1 for char in text_lower if char in ukrainian_chars)
        total_chars = len([char for char in text_lower if char.isalpha()])
        
        if total_chars == 0:
            return False
            
        ukrainian_percentage = ukrainian_char_count / total_chars
        return ukrainian_percentage > 0.3

    def generate_smart_caption(self, meme_data: Dict) -> str:
        """Генерує розумні підписи з українським контекстом"""
        current_hour = datetime.now().hour
        time_category = self.get_time_category(current_hour)
        
        # Вибираємо підпис за часом дня
        time_caption = random.choice(self.time_based_captions[time_category])
        
        # Обробляємо назву мему
        title = meme_data.get('title', '')
        source = meme_data.get('source', 'unknown')
        score = meme_data.get('score', 0)
        
        # Додаємо інфо про локалізацію
        localization_note = ""
        if meme_data.get('localized'):
            localization_note = " 🤖"
        
        # Генеруємо хештеги (2-3 випадкових)
        hashtags = random.sample(self.trending_hashtags, 3)
        hashtag_str = ' '.join(hashtags)
        
        # Формуємо фінальний підпис
        if title:
            caption = f"{time_caption}\n\n💭 {title}{localization_note}\n\n"
        else:
            caption = f"{time_caption}\n\n"
        
        # Додаємо метаінформацію
        caption += f"📊 Популярність: {score}\n"
        caption += f"🔗 Джерело: {source}\n\n"
        caption += hashtag_str
        
        return caption

    def get_fallback_meme(self) -> Dict:
        """Резервні меми коли всі API не працюють"""
        fallback_memes = [
            {
                'url': 'https://i.imgflip.com/1bij.jpg',
                'title': 'Коли всі API впали, але Бобік не здається! 💪',
                'score': 9999,
                'source': 'fallback'
            },
            {
                'url': 'https://i.imgflip.com/30b1gx.jpg', 
                'title': 'Інтернет проти стабільної роботи API',
                'score': 8888,
                'source': 'fallback'
            }
        ]
        
        return random.choice(fallback_memes)

    async def post_meme_to_channel_advanced(self) -> bool:
        """Покращена публікація з AI локалізацією та аналітикою"""
        try:
            meme = self.get_meme_with_fallback()
            if not meme:
                logger.error("❌ Не вдалося отримати жодного мему")
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
            
            # Оновлюємо статистику
            current_time = datetime.now()
            self.stats['posts_today'] += 1
            self.stats['total_posts'] += 1
            self.stats['successful_posts'] += 1
            self.stats['last_post_time'] = current_time
            
            logger.info(f"✅ Мем опубліковано! ID: {result.message_id}, Час: {current_time.strftime('%H:%M')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка публікації: {e}")
            self.stats['failed_posts'] += 1
            return False

    def should_post_now(self) -> bool:
        """Перевіряє чи треба публікувати зараз"""
        current_time = datetime.now().strftime('%H:%M')
        return current_time in self.posting_schedule

    async def scheduler_loop(self):
        """Основний цикл планувальника"""
        logger.info("🕐 Покращений планувальник запущений!")
        
        while self.scheduler_running:
            try:
                if self.should_post_now():
                    kyiv_time = (datetime.now().hour + 2) % 24
                    logger.info(f"⏰ Час публікації: {datetime.now().strftime('%H:%M')} UTC (Київ: {kyiv_time:02d}:{datetime.now().minute:02d})")
                    
                    success = await self.post_meme_to_channel_advanced()
                    
                    if success:
                        logger.info("✅ Мем успішно опубліковано за розкладом")
                    else:
                        logger.error("❌ Помилка публікації за розкладом")
                    
                    # Чекаємо 70 секунд щоб не повторювати в ту ж хвилину
                    await asyncio.sleep(70)
                else:
                    # Перевіряємо кожні 30 секунд
                    await asyncio.sleep(30)
                    
            except Exception as e:
                logger.error(f"❌ Помилка в планувальнику: {e}")
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
            logger.info("📅 Покращений автоматичний розклад активовано!")

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
                "🐕 **Покращене головне меню Бобіка 2.0**\n\n🤖 AI локалізація активна\n📡 Множинні API джерела\n🇺🇦 Оптимізовано для України\n\nОберіть дію:",
                reply_markup=self.create_main_menu(),
                parse_mode='Markdown'
            )
            
        elif data == "api_status":
            await query.edit_message_text("🔍 Тестую всі API джерела...")
            api_results = self.test_meme_apis()
            
            status_text = "📡 **Статус API джерел:**\n\n"
            
            working_apis = sum(api_results.values())
            total_apis = len(api_results)
            
            for api_name, is_working in api_results.items():
                status_icon = "✅" if is_working else "❌"
                status_text += f"{status_icon} {api_name}\n"
            
            status_text += f"\n📊 **Підсумок:** {working_apis}/{total_apis} працюють"
            
            await query.edit_message_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Оновити", callback_data="api_status"),
                    InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
                ]]),
                parse_mode='Markdown'
            )
            
        elif data == "ai_status":
            ai_text = "🤖 **Статус AI інтеграції:**\n\n"
            
            if OPENAI_AVAILABLE and self.openai_client:
                ai_text += "✅ **OpenAI**: Підключено та активно\n"
                ai_text += f"📊 **Локалізовано постів**: {self.stats['localized_posts']}\n"
                ai_text += "🇺🇦 **Функції**: Автоматична локалізація мемів\n"
            elif OPENAI_AVAILABLE:
                ai_text += "⚠️ **OpenAI**: Доступно, але не налаштовано\n"
                ai_text += "🔑 **Потрібно**: Встановити OPENAI_API_KEY\n"
            else:
                ai_text += "❌ **OpenAI**: Не встановлено\n"
                ai_text += "⚡ **Статус**: Працюємо без AI (базова локалізація)"
            
            await query.edit_message_text(
                ai_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )
            
        elif data == "test_post":
            await query.edit_message_text("🧪 Публікую тестовий мем з AI обробкою...")
            success = await self.post_meme_to_channel_advanced()
            
            if success:
                text = "✅ **Тестовий мем успішно опубліковано!**\n\n"
                text += f"🤖 AI локалізація: {'Активна' if self.openai_client else 'Вимкнена'}\n"
                text += "Перевірте канал @BobikFun"
            else:
                text = "❌ **Помилка публікації**\n\nПеревірте налаштування бота та статус API"
                
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )
            
        elif data == "random_meme":
            await query.edit_message_text("🔍 Шукаю найкращий мем...")
            
            meme = self.get_meme_with_fallback()
            if meme:
                caption = self.generate_smart_caption(meme)
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=meme['url'],
                    caption=caption
                )
                await query.edit_message_text(
                    "✅ **Мем відправлено!**",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🎲 Ще мем", callback_data="random_meme"), 
                        InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
                    ]]),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **Не вдалося знайти мем**\n\nСпробуйте ще раз",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Спробувати ще", callback_data="random_meme"), 
                        InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
                    ]]),
                    parse_mode='Markdown'
                )
                
        elif data == "schedule":
            schedule_text = f"""
⏰ **Розклад автопублікацій (Київський час UTC+2):**

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
            await query.edit_message_text(
                schedule_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )
            
        elif data == "management":
            status = "🟢 Активний" if self.scheduler_running else "🔴 Зупинений"
            await query.edit_message_text(
                f"⚙️ **Управління ботом**\n\nПоточний статус: {status}\n\nОберіть дію:",
                reply_markup=self.create_management_menu(),
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
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Ще один ЗАРАЗ", callback_data="post_now"), 
                    InlineKeyboardButton("⬅️ Назад", callback_data="management")
                ]]),
                parse_mode='Markdown'
            )
            
        elif data == "analytics":
            analytics_text = self.get_analytics()
            await query.edit_message_text(
                analytics_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )
            
        elif data == "help":
            help_text = f"""
ℹ️ **Довідка по боту Бобік 2.0:**

🎯 **Основні функції:**
• Автоматична публікація {len(self.posting_schedule)} мемів/день
• 🤖 AI локалізація українською
• 📡 {sum(len(sources) if isinstance(sources, dict) else len(sources) for sources in self.meme_sources.values())}+ API джерел
• 🇺🇦 Оптимізовано для України

📱 **Команди:**
• **📊 Аналітика** - статистика каналу
• **🧪 Тест пост** - швидка публікація
• **🎲 Мем** - випадковий мем приватно
• **📅 Розклад** - план публікацій
• **⚙️ Управління** - запуск/зупинка

🤖 **AI статус:** {'✅ Активний' if self.openai_client else '❌ Вимкнений'}
📡 **API джерел:** {sum(len(sources) if isinstance(sources, dict) else len(sources) for sources in self.meme_sources.values())}
"""
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )

    async def handle_permanent_menu(self, update, context):
        """Обробник постійного меню"""
        text = update.message.text
        
        if text == "📊 Аналітика":
            analytics_text = self.get_analytics()
            await update.message.reply_text(analytics_text, parse_mode='Markdown')
            
        elif text == "🧪 Тест пост":
            await update.message.reply_text("🧪 Публікую тестовий мем...")
            success = await self.post_meme_to_channel_advanced()
            
            if success:
                await update.message.reply_text("✅ **Тестовий мем опубліковано!**", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ **Помилка публікації**", parse_mode='Markdown')
                
        elif text == "🎲 Мем":
            await update.message.reply_text("🔍 Шукаю найкращий мем...")
            
            meme = self.get_meme_with_fallback()
            if meme:
                caption = self.generate_smart_caption(meme)
                await update.message.reply_photo(photo=meme['url'], caption=caption)
            else:
                await update.message.reply_text("😔 Не знайшов мему, спробуй ще раз!")
                
        elif text == "📅 Розклад":
            schedule_text = f"""
⏰ **Розклад автопублікацій (Київський час):**

📊 **Всього: {len(self.posting_schedule)} постів/день**
🔄 **Статус: {'✅ Активний' if self.scheduler_running else '❌ Вимкнений'}**

🌅 05:00, 07:00, 09:00 - Ранок
🌞 11:30, 13:00, 15:00, 17:00 - День  
🌆 19:00, 21:00, 22:30, 23:45 - Вечір
"""
            await update.message.reply_text(schedule_text, parse_mode='Markdown')
            
        elif text == "⚙️ Управління":
            status = "🟢 Активний" if self.scheduler_running else "🔴 Зупинений"
            await update.message.reply_text(
                f"⚙️ **Управління ботом**\n\nСтатус: {status}",
                reply_markup=self.create_management_menu(),
                parse_mode='Markdown'
            )
            
        elif text == "📈 API Статус":
            await update.message.reply_text("🔍 Перевіряю API...")
            api_results = self.test_meme_apis()
            working = sum(api_results.values())
            total = len(api_results)
            
            await update.message.reply_text(
                f"📡 **API Статус:** {working}/{total} працюють",
                parse_mode='Markdown'
            )
            
        elif text == "🤖 AI Статус":
            if self.openai_client:
                ai_text = f"🤖 **AI активний**\n\n📊 Локалізовано: {self.stats['localized_posts']} постів"
            else:
                ai_text = "🤖 **AI вимкнений**\n\nПрацюємо в базовому режимі"
                
            await update.message.reply_text(ai_text, parse_mode='Markdown')
            
        elif text == "ℹ️ Допомога":
            help_text = f"""
ℹ️ **Бобік 2.0 - AI Мем-Бот**

🤖 **AI:** {'✅ Активний' if self.openai_client else '❌ Вимкнений'}
📡 **API:** {sum(len(sources) if isinstance(sources, dict) else len(sources) for sources in self.meme_sources.values())} джерел
📊 **Постів:** {len(self.posting_schedule)}/день
🇺🇦 **Оптимізовано для України**
"""
            await update.message.reply_text(help_text, parse_mode='Markdown')

    def get_analytics(self) -> str:
        """Генерує розширену аналітику"""
        success_rate = 0
        if self.stats['successful_posts'] + self.stats['failed_posts'] > 0:
            success_rate = (self.stats['successful_posts'] / 
                          (self.stats['successful_posts'] + self.stats['failed_posts']) * 100)
        
        # Топ джерела
        top_sources = sorted(
            self.stats['content_sources'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        analytics = f"""
📊 **Аналітика Бобіка 2.0:**

📈 **Основна статистика:**
• Постів сьогодні: {self.stats['posts_today']}/11
• Всього постів: {self.stats['total_posts']}
• Успішних: {self.stats['successful_posts']}
• Успішність: {success_rate:.1f}%

🤖 **AI метрики:**
• Локалізовано постів: {self.stats['localized_posts']}
• AI статус: {'✅ Активний' if self.openai_client else '❌ Вимкнений'}

📡 **Топ джерела:**"""
        
        for source, count in top_sources:
            analytics += f"\n• {source}: {count}"
        
        analytics += f"""

🇺🇦 **Українізація:**
• Часовий пояс: UTC+2 (Київ)
• Аудиторія: IT 16-35 років
• Локалізація: {'AI + ручна' if self.openai_client else 'Базова'}
"""
        
        return analytics

    async def start_command(self, update, context):
        permanent_menu = self.create_permanent_menu()
        await update.message.reply_text(
            "🐕 **Привіт! Я покращений Бобік 2.0!**\n\n"
            "🚀 **Нові можливості:**\n"
            "• 🤖 AI локалізація мемів для українців\n"
            "• 📡 Множинні API з відмовостійкістю\n"
            "• 🇺🇦 Адаптований розклад (UTC+2)\n"
            "• 📊 Розширена аналітика джерел\n"
            "• 11 автопостів на день\n\n"
            "📱 **Меню з'явилося внизу екрану!**\n"
            f"🤖 **AI статус**: {'✅ Активний' if self.openai_client else '⚠️ Базовий режим'}\n\n"
            "🔗 **Канал:** @BobikFun",
            reply_markup=permanent_menu,
            parse_mode='Markdown'
        )

    async def menu_command(self, update, context):
        permanent_menu = self.create_permanent_menu()
        await update.message.reply_text(
            "📱 **Постійне меню активовано!**",
            reply_markup=permanent_menu,
            parse_mode='Markdown'
        )

def main():
    """Головна функція з покращеннями"""
    bot = AdvancedBobikBot()
    
    # Створюємо додаток
    application = Application.builder().token(bot.bot_token).build()
    
    # Додаємо команди
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("menu", bot.menu_command))
    
    # Додаємо обробник кнопок меню
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Додаємо обробник постійного меню
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.handle_permanent_menu
    ))
    
    # ЗАПУСКАЄМО АВТОМАТИЧНИЙ ПЛАНУВАЛЬНИК
    bot.start_scheduler()
    
    logger.info("🚀 Бобік 2.0 з AI локалізацією запущений!")
    logger.info(f"🤖 AI статус: {'✅ Активний' if bot.openai_client else '⚠️ Базовий режим'}")
    logger.info(f"📅 Буде публікувати {len(bot.posting_schedule)} мемів на день")
    logger.info("🇺🇦 Оптимізовано для української аудиторії!")
    
    # Запускаємо бота
    application.run_polling()

if __name__ == "__main__":
    main()
