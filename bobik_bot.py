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

# Для ChatGPT інтеграції
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI не встановлено. Працюємо без AI локалізації.")

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedBobikBot:
    def __init__(self):
        self.bot_token = "7882259321:AAGGqql6LD6bzLHTOb1HdKUYs2IJBZqsd6E"
        self.channel_id = "@BobikFun"
        
        # OpenAI клієнт (опціонально)
        self.openai_client = None
        if OPENAI_AVAILABLE:
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("🤖 ChatGPT інтеграція активована")
            else:
                logger.info("🔑 OPENAI_API_KEY не знайдено. Працюємо без AI.")
        
        # Покращена статистика з українізацією
        self.stats = {
            'posts_today': 0,
            'total_posts': 0,
            'last_post_time': None,
            'successful_posts': 0,
            'failed_posts': 0,
            'best_engagement_time': None,
            'daily_stats': {},
            'posted_memes': set(),
            'posted_hashes': set(),  # Хеші для дедуплікації
            'hourly_posts': {},
            'last_api_check': None,
            'localized_posts': 0,  # Кількість локалізованих постів
            'api_failures': {},     # Статистика відмов API
            'content_sources': {}   # Статистика джерел контенту
        }
        
        # Оптимальний розклад для української аудиторії (UTC+2 = Київський час)
        self.posting_schedule = [
            "03:00",  # 05:00 Київ - Рання пташка
            "05:00",  # 07:00 Київ - Ранкова кава ☕
            "07:00",  # 09:00 Київ - Початок робочого дня 💼
            "09:30",  # 11:30 Київ - Перед обідом
            "11:00",  # 13:00 Київ - Обідня перерва 🍽️
            "13:00",  # 15:00 Київ - Після обіду ⚡
            "15:00",  # 17:00 Київ - Кінець робочого дня
            "17:00",  # 19:00 Київ - Вечерня активність 🏠
            "19:00",  # 21:00 Київ - Прайм-тайм 📺
            "20:30",  # 22:30 Київ - Пізній вечір
            "21:45"   # 23:45 Київ - Нічні сови 🦉
        ]
        
        self.scheduler_running = False
        
        # Покращені джерела мемів з відмовостійкістю та пріоритетами
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
                'software_gore': "https://api.reddit.com/r/softwaregore/hot.json?limit=20"
            },
            'backup': {
                'imgflip': "https://api.imgflip.com/get_memes",
                'random_api': "https://some-random-api.ml/meme"
            }
        }
        
        # Українські контекстні підписи з покращеною локалізацією
        self.ukrainian_context = {
            'work_terms': {
                'job': 'робота', 'work': 'праця', 'office': 'офіс', 'boss': 'бос',
                'deadline': 'дедлайн', 'meeting': 'мітинг', 'zoom': 'зум',
                'remote work': 'віддалена робота', 'freelance': 'фріланс',
                'salary': 'зарплата', 'overtime': 'переробка'
            },
            'tech_terms': {
                'code': 'код', 'bug': 'баг', 'debug': 'дебаг', 'deploy': 'деплой',
                'server': 'сервер', 'database': 'база даних', 'api': 'апі',
                'frontend': 'фронтенд', 'backend': 'бекенд', 'git': 'гіт'
            },
            'life_terms': {
                'morning': 'ранок', 'coffee': 'кава', 'monday': 'понеділок',
                'weekend': 'вихідні', 'vacation': 'відпустка', 'home': 'дім',
                'food': 'їжа', 'sleep': 'сон', 'money': 'гроші'
            }
        }
        
        # Українські підписи за часом дня
        self.time_based_captions = {
            'early_morning': [
                "🌅 Ранні пташки, цей мем для вас!",
                "☕ Перша кава та свіжий мем - ідеальний ранок",
                "🐕 Бобік вже не спить, а ти?",
                "🌞 Новий день = новий мем від Бобіка"
            ],
            'morning': [
                "🌅 Коли прокинувся і зрозумів, що сьогодні не вихідний:",
                "☕ Ранкова кава і мем - єдине що тримає на плаву",
                "💼 Початок робочого дня в стилі Бобіка",
                "😴 Будильник проти твоєї волі до життя:"
            ],
            'work_hours': [
                "💻 Коли бос питає про прогрес, а ти дивився меми:",
                "📱 Офіційна перерва на мем серед робочого хаосу",
                "🤔 Коли робиш вигляд, що працюєш:",
                "💼 Реальність офісного життя:",
                "⌨️ Код vs мої очікування:",
                "📧 Коли в п'ятницю надходить 'терміновий' проект:"
            ],
            'lunch': [
                "🍔 Обідня перерва - священний час кожного працівника",
                "🥪 Коли їси і дивишся меми одночасно = мультитаскінг",
                "😋 Їжа смачніша під мемчики від Бобіка",
                "🍕 Планував здоровий обід vs реальність:",
                "🥗 Дієта vs те, що насправді їм:"
            ],
            'afternoon': [
                "⚡ Післяобідній енергетичний спад vs дедлайни:",
                "😴 15:00 - час коли продуктивність йде спати",
                "💼 Друга половина робочого дня like:",
                "🔥 Коли до кінця робочого дня залишилося трохи"
            ],
            'evening': [
                "🏠 Нарешті дома! Час для якісних мемів",
                "🛋️ Після роботи тільки диван і мемаси",
                "📺 Коли вибираєш між серіалом і мемами:",
                "🌆 Кінець робочого дня - почалося справжнє життя",
                "🎮 Коли планував продуктивний вечір:",
                "🍿 Ідеальний вечір: мемчики + щось смачне"
            ],
            'late_evening': [
                "🌃 Вечірній прайм-тайм мемів від Бобіка",
                "📱 Коли скролиш меми замість справ:",
                "🛋️ Вечірній чіл режим активовано",
                "🎬 Кращий вечірній контент - це меми"
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
        
        # Українські хештеги з покращеною ротацією
        self.trending_hashtags = [
            "#мемчик", "#гумор", "#релейтабл", "#настрій", "#життя", 
            "#робота", "#айті", "#понеділок", "#кава", "#україна", 
            "#бобік", "#смішно", "#мемас", "#офісlife", "#студентlife", 
            "#дорослеlife", "#київ", "#львів", "#програміст", "#фріланс",
            "#віддаленаробота", "#дедлайн", "#мітинг", "#вихідні"
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
                InlineKeyboardButton("📈 Статус API", callback_data="api_status")
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
                InlineKeyboardButton("🔧 Тест API", callback_data="test_apis"),
                InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def test_meme_apis(self) -> Dict[str, bool]:
        """Тестує всі API джерела мемів"""
        api_status = {}
        
        for category, sources in self.meme_sources.items():
            for name, url in sources.items():
                try:
                    logger.info(f"Тестую API: {name}")
                    
                    headers = {'User-Agent': 'BobikBot/2.0 (Ukrainian Meme Bot)'}
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    api_status[f"{category}_{name}"] = response.status_code == 200
                    
                    if response.status_code == 200:
                        logger.info(f"✅ {name} працює")
                    else:
                        logger.warning(f"⚠️ {name} повернув код {response.status_code}")
                        
                except Exception as e:
                    api_status[f"{category}_{name}"] = False
                    logger.error(f"❌ {name} недоступний: {e}")
                    
        return api_status

    def get_meme_with_fallback(self) -> Optional[Dict]:
        """Отримує мем з системою fallback та покращеної фільтрації"""
        
        # Пробуємо по пріоритету: primary -> tech -> secondary -> backup
        source_priority = ['primary', 'tech_specific', 'secondary', 'backup']
        
        for category in source_priority:
            sources = self.meme_sources.get(category, {})
            
            for source_name, api_url in sources.items():
                try:
                    logger.info(f"Спробую {source_name} з {category}")
                    
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
            raise Exception(f"HTTP {response.status_code}")
            
        data = response.json()
        
        # Обробляємо різні формати API
        if 'reddit.com' in api_url:
            return self.parse_reddit_response(data, source_name)
        elif 'meme-api' in api_url:
            return self.parse_meme_api_response(data, source_name)  
        elif 'imgflip' in api_url:
            return self.parse_imgflip_response(data, source_name)
        else:
            return self.parse_generic_response(data, source_name)

    def parse_reddit_response(self, data: Dict, source: str) -> Optional[Dict]:
        """Парсить відповідь Reddit API"""
        
        posts = data.get('data', {}).get('children', [])
        
        # Фільтруємо найякісніші пости
        quality_posts = []
        for post in posts:
            post_data = post.get('data', {})
            
            if self.is_valid_reddit_post(post_data):
                quality_posts.append({
                    'url': post_data.get('url'),
                    'title': post_data.get('title', ''),
                    'score': post_data.get('score', 0),
                    'subreddit': post_data.get('subreddit', ''),
                    'source': source,
                    'created_utc': post_data.get('created_utc', 0)
                })
        
        if quality_posts:
            # Сортуємо за популярністю та повертаємо найкращий
            quality_posts.sort(key=lambda x: x['score'], reverse=True)
            return quality_posts[0]
            
        return None

    def parse_meme_api_response(self, data: Dict, source: str) -> Optional[Dict]:
        """Парсить відповідь meme-api"""
        
        if 'url' in data and 'title' in data:
            return {
                'url': data.get('url'),
                'title': data.get('title', 'Мем'),
                'score': data.get('ups', 100),  # Дефолтний score
                'subreddit': data.get('subreddit', 'memes'),
                'source': source,
                'created_utc': int(time.time())
            }
        return None

    def parse_imgflip_response(self, data: Dict, source: str) -> Optional[Dict]:
        """Парсить відповідь ImgFlip API"""
        
        memes = data.get('data', {}).get('memes', [])
        if memes:
            meme = random.choice(memes[:20])  # Топ 20 популярних мемів
            return {
                'url': meme.get('url'),
                'title': meme.get('name', 'ImgFlip Мем'),
                'score': 500,  # Середній score для imgflip
                'subreddit': 'imgflip',
                'source': source,
                'created_utc': int(time.time())
            }
        return None

    def parse_generic_response(self, data: Dict, source: str) -> Optional[Dict]:
        """Парсить загальний формат відповіді"""
        
        # Спробуємо знайти основні поля в різних варіантах
        url = data.get('url') or data.get('image') or data.get('link')
        title = data.get('title') or data.get('caption') or data.get('text') or 'Мем'
        
        if url:
            return {
                'url': url,
                'title': title,
                'score': data.get('score', data.get('upvotes', 100)),
                'subreddit': data.get('subreddit', 'generic'),
                'source': source,
                'created_utc': int(time.time())
            }
        return None

    def is_valid_reddit_post(self, post_data: Dict) -> bool:
        """Перевіряє валідність Reddit поста"""
        
        url = post_data.get('url', '')
        title = post_data.get('title', '').lower()
        score = post_data.get('score', 0)
        
        # Перевірка формату зображення
        if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', 'i.redd.it', 'i.imgur.com']):
            return False
        
        # Мінімальний score (адаптивний)
        min_score = 100 if datetime.now().hour in [7, 8, 9, 12, 13, 18, 19, 20] else 50
        if score < min_score:
            return False
        
        # Фільтр неприйнятного контенту
        blacklist = ['nsfw', 'porn', 'sex', 'nude', 'politics', 'trump', 'biden', 'election']
        if any(word in title for word in blacklist):
            return False
        
        return True

    def is_quality_meme_ukraine(self, meme_data: Dict) -> bool:
        """Перевіряє якість мему для української аудиторії"""
        
        if not meme_data:
            return False
            
        # Перевірка дублікатів по хешу
        meme_hash = self.generate_meme_hash(meme_data)
        if meme_hash in self.stats['posted_hashes']:
            logger.info(f"❌ Дублікат знайдено: {meme_data.get('title', '')}")
            return False
        
        # Перевірка релевантності для України
        if not self.is_relevant_for_ukraine(meme_data):
            return False
        
        # Перевірка URL зображення
        url = meme_data.get('url', '')
        if not url or not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', 'i.redd.it', 'i.imgur.com']):
            return False
        
        # Додаємо до історії
        self.stats['posted_hashes'].add(meme_hash)
        
        # Очищуємо історію якщо забагато (залишаємо останні 1000)
        if len(self.stats['posted_hashes']) > 1000:
            self.stats['posted_hashes'] = set(list(self.stats['posted_hashes'])[-500:])
        
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
            'halloween costumes', 'american football', 'nfl', 'mlb',
            'dollar bills', 'american school', 'american college'
        ]
        
        for term in ukraine_blacklist:
            if term in title:
                logger.info(f"❌ Неактуально для України: {term} in {title}")
                return False
        
        # Whitelist універсальних тем
        universal_topics = [
            'work', 'job', 'monday', 'coffee', 'weekend', 'sleep', 'food',
            'internet', 'phone', 'computer', 'programming', 'code', 'bug',
            'meeting', 'boss', 'salary', 'home', 'family', 'friends',
            'netflix', 'youtube', 'instagram', 'tiktok', 'meme', 'funny'
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

            Правила адаптації:
            - Переклади на українську якщо потрібно
            - Заміни незрозумілі американські посилання на українські аналоги
            - Зберігай гумор та суть
            - Використовуй сучасний український інтернет-сленг
            - Максимум 120 символів
            - НЕ додавай емодзі (вони будуть додані окремо)

            Українська назва:
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            
            localized_title = response.choices[0].message.content.strip()
            
            # Очищуємо від зайвих символів та фраз
            localized_title = localized_title.replace('"', '').replace('Українська назва:', '').strip()
            
            if localized_title and len(localized_title) > 10:
                meme_data['title'] = localized_title
                meme_data['localized'] = True
                logger.info(f"🇺🇦 Локалізовано: {original_title[:50]}... → {localized_title[:50]}...")
            
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
        return ukrainian_percentage > 0.3  # Більше 30% українських символів

    def get_time_category(self, hour: int) -> str:
        """Визначає категорію часу для підбору підписів (українська часова зона)"""
        
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
            
            # Детальна статистика
            if hour_key not in self.stats['hourly_posts']:
                self.stats['hourly_posts'][hour_key] = []
            self.stats['hourly_posts'][hour_key].append({
                'time': current_time.isoformat(),
                'meme_title': meme.get('title', ''),
                'source': meme.get('source', ''),
                'localized': meme.get('localized', False),
                'message_id': result.message_id
            })
            
            logger.info(f"✅ Мем опубліковано! ID: {result.message_id}, Час: {current_time.strftime('%H:%M')}, Джерело: {meme.get('source', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка публікації: {e}")
            self.stats['failed_posts'] += 1
            return False

    def get_fallback_meme(self) -> Dict:
        """Резервні меми коли всі API не працюють"""
        
        fallback_memes = [
            {
                'url': 'https://i.imgflip.com/1bij.jpg',
                'title': 'Коли всі API впали, але Бобік не здається! 💪',
                'score': 9999,
                'source': 'fallback',
                'subreddit': 'bobik_emergency'
            },
            {
                'url': 'https://i.imgflip.com/30b1gx.jpg', 
                'title': 'Інтернет проти стабільної роботи API',
                'score': 8888,
                'source': 'fallback',
                'subreddit': 'bobik_emergency'
            },
            {
                'url': 'https://i.imgflip.com/1otk96.jpg',
                'title': 'Коли є резервний план на всі випадки життя',
                'score': 7777,
                'source': 'fallback',
                'subreddit': 'bobik_emergency'
            }
        ]
        
        return random.choice(fallback_memes)

    def should_post_now(self) -> bool:
        """Перевіряє чи треба публікувати зараз"""
        current_time = datetime.now().strftime('%H:%M')
        return current_time in self.posting_schedule

    async def scheduler_loop(self):
        """Основний цикл планувальника з покращеним логуванням"""
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
        """Обробник натискань кнопок меню з новими функціями"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "main_menu":
            await query.edit_message_text(
                "🐕 **Покращене головне меню Бобіка**\n\n🤖 AI локалізація активна\n📡 Множинні API джерела\n🇺🇦 Оптимізовано для України\n\nОберіть дію:",
                reply_markup=self.create_main_menu(),
                parse_mode='Markdown'
            )
            
        elif data == "api_status":
            await query.edit_message_text("🔍 Тестую всі API джерела...")
            api_results = self.test_meme_apis()
            
            status_text = "📡 **Статус API джерел:**\n\n"
            
            working_apis = 0
            total_apis = len(api_results)
            
            for api_name, is_working in api_results.items():
                status_icon = "✅" if is_working else "❌"
                category = api_name.split('_')[0]
                name = '_'.join(api_name.split('_')[1:])
                status_text += f"{status_icon} **{category}**: {name}\n"
                if is_working:
                    working_apis += 1
            
            status_text += f"\n📊 **Підсумок:** {working_apis}/{total_apis} працюють\n"
            
            if working_apis == 0:
                status_text += "🆘 **Критично**: Всі API недоступні!"
            elif working_apis < total_apis // 2:
                status_text += "⚠️ **Увага**: Багато API недоступні"
            else:
                status_text += "✅ **Добре**: Достатньо робочих API"
            
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
                ai_text += "🎯 **Якість**: Покращена релевантність для України\n\n"
                ai_text += "💡 **AI допомагає:**\n"
                ai_text += "• Перекладати англійські меми\n"
                ai_text += "• Адаптувати культурні посилання\n"
                ai_text += "• Покращувати зрозумілість для українців"
            elif OPENAI_AVAILABLE:
                ai_text += "⚠️ **OpenAI**: Доступно, але не налаштовано\n"
                ai_text += "🔑 **Потрібно**: Встановити OPENAI_API_KEY\n"
                ai_text += "📝 **Команда**: `export OPENAI_API_KEY=your_key`"
            else:
                ai_text += "❌ **OpenAI**: Не встановлено\n"
                ai_text += "📦 **Встановлення**: `pip install openai`\n"
                ai_text += "⚡ **Статус**: Працюємо без AI (базова локалізація)"
            
            await query.edit_message_text(
                ai_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )
            
        elif data == "test_apis":
            await query.edit_message_text("🧪 Тестую всі API та публікую результати...")
            
            api_results = self.test_meme_apis()
            working_count = sum(api_results.values())
            
            test_text = f"🔬 **Результати тестування API:**\n\n"
            test_text += f"📊 Працюючих API: {working_count}/{len(api_results)}\n\n"
            
            # Спробуємо отримати мем
            meme = self.get_meme_with_fallback()
            if meme:
                test_text += f"✅ **Мем отримано**: {meme.get('source', 'unknown')}\n"
                test_text += f"📝 **Назва**: {meme.get('title', 'Без назви')[:50]}...\n"
                test_text += f"🎯 **Локалізовано**: {'Так' if meme.get('localized') else 'Ні'}\n\n"
                test_text += "🚀 Готовий до публікації!"
            else:
                test_text += "❌ **Помилка**: Не вдалося отримати мем з жодного API"
            
            await query.edit_message_text(
                test_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="management")]]),
                parse_mode='Markdown'
            )
            
        # ... (решта обробників кнопок аналогічно до оригіналу, але з покращеннями)
        
        elif data == "test_post":
            await query.edit_message_text("🧪 Публікую тестовий мем з AI обробкою...")
            success = await self.post_meme_to_channel_advanced()
            
            if success:
                text = "✅ **Тестовий мем успішно опубліковано!**\n\n"
                text += f"🤖 AI локалізація: {'Активна' if self.openai_client else 'Вимкнена'}\n"
                text += f"📊 Локалізовано постів: {self.stats['localized_posts']}\n\n"
                text += "Перевірте канал @BobikFun"
            else:
                text = "❌ **Помилка публікації**\n\nПеревірте налаштування бота та статус API"
                
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]),
                parse_mode='Markdown'
            )

    def create_permanent_menu(self) -> ReplyKeyboardMarkup:
        """Створює постійне меню внизу екрану"""
        keyboard = [
            ["📊 Аналітика", "🧪 Тест пост"],
            ["🎲 Мем", "📅 Розклад"], 
            ["⚙️ Управління", "📡 API Статус"],
            ["🤖 AI Статус", "ℹ️ Допомога"]
        ]
        return ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True,
            one_time_keyboard=False,
            selective=False,
            input_field_placeholder="Обери дію з меню 👇"
        )

    def get_analytics(self) -> str:
        """Генерує розширену аналітику з AI метриками"""
        
        success_rate = 0
        if self.stats['successful_posts'] + self.stats['failed_posts'] > 0:
            success_rate = (self.stats['successful_posts'] / 
                          (self.stats['successful_posts'] + self.stats['failed_posts']) * 100)
        
        # Статистика джерел
        top_sources = sorted(
            self.stats['content_sources'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        analytics = f"""
📊 **Розширена аналітика Бобіка 2.0:**

📈 **Основна статистика:**
• Постів сьогодні: {self.stats['posts_today']}/11
• Всього постів: {self.stats['total_posts']}
• Успішних: {self.stats['successful_posts']}
• Невдалих: {self.stats['failed_posts']}
• Успішність: {success_rate:.1f}%

🤖 **AI метрики:**
• Локалізовано постів: {self.stats['localized_posts']}
• AI статус: {'✅ Активний' if self.openai_client else '❌ Вимкнений'}

📡 **Топ джерела контенту:**"""
        
        for source, count in top_sources:
            analytics += f"\n• {source}: {count} постів"
        
        analytics += f"""

🌍 **Українізація:**
• Часовий пояс: UTC+2 (Київ)
• Контекст: IT аудиторія 16-35 років
• Локалізація: {'AI + ручна' if self.openai_client else 'Тільки ручна'}
"""
        
        return analytics

    # ... (додаткові методи аналогічно до оригіналу з покращеннями)

    async def start_command(self, update, context):
        permanent_menu = self.create_permanent_menu()
        await update.message.reply_text(
            "🐕 **Привіт! Я покращений Бобік 2.0!**\n\n"
            "🚀 **Нові можливості:**\n"
            "• 🤖 AI локалізація мемів для українців\n"
            "• 📡 Множинні API з відмовостійкістю\n"
            "• 🇺🇦 Адаптований розклад (UTC+2)\n"
            "• 📊 Розширена аналітика джерел\n"
            "• 🎯 Покращена фільтрація релевантності\n\n"
            "📱 **Постійне меню з'явилося внизу екрану!**\n"
            f"🤖 **AI статус**: {'✅ Активний' if self.openai_client else '⚠️ Базовий режим'}\n\n"
            "🔗 **Канал:** @BobikFun",
            reply_markup=permanent_menu,
            parse_mode='Markdown'
        )

    # ... (решта методів аналогічно до оригіналу)

def main():
    """Головна функція з покращеннями"""
    bot = AdvancedBobikBot()
    
    # Створюємо додаток
    application = Application.builder().token(bot.bot_token).build()
    
    # Додаємо всі команди та обробники (аналогічно до оригіналу)
    application.add_handler(CommandHandler("start", bot.start_command))
    # ... (додати всі інші обробники)
    
    # ЗАПУСКАЄМО АВТОМАТИЧНИЙ ПЛАНУВАЛЬНИК
    bot.start_scheduler()
    
    logger.info("🚀 Покращений Бобік 2.0 з AI локалізацією запущений!")
    logger.info(f"🤖 AI статус: {'✅ Активний' if bot.openai_client else '⚠️ Базовий режим'}")
    logger.info(f"📅 Буде публікувати {len(bot.posting_schedule)} мемів на день")
    logger.info("🇺🇦 Оптимізовано для української аудиторії!")
    
    # Запускаємо бота
    application.run_polling()

if __name__ == "__main__":
    main()
