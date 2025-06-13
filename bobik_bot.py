import requests
import asyncio
import random
import logging
import json
import time
import os
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from typing import Dict, List, Optional
import threading

# AI інтеграція
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
        
        # AI клієнт
        self.openai_client = None
        if OPENAI_AVAILABLE:
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("🤖 ChatGPT інтеграція активована")
            else:
                logger.info("🔑 OPENAI_API_KEY не знайдено в environment variables")
        
        # Статистика
        self.stats = {
            'posts_today': 0,
            'total_posts': 0,
            'last_post_time': None,
            'successful_posts': 0,
            'failed_posts': 0,
            'localized_posts': 0,
            'posted_memes': set()
        }
        
        # Покращений розклад (UTC) - для України додайте +2 години
        self.posting_schedule = [
            "05:00",  # 07:00 Київ - Ранкова кава ☕
            "07:00",  # 09:00 Київ - Початок робочого дня 💼
            "09:30",  # 11:30 Київ - Перед обідом
            "11:00",  # 13:00 Київ - Обідня перерва 🍽️
            "13:00",  # 15:00 Київ - Після обіду ⚡
            "15:00",  # 17:00 Київ - Кінець робочого дня
            "17:00",  # 19:00 Київ - Вечерня активність 🏠
            "19:00",  # 21:00 Київ - Прайм-тайм 📺
            "20:30",  # 22:30 Київ - Пізній вечір
            "21:45",  # 23:45 Київ - Нічні сови 🦉
            "23:00"   # 01:00 Київ - Пізно працюючі
        ]
        
        self.scheduler_running = False
        
        # Покращені джерела мемів
        self.meme_sources = [
            "https://meme-api.herokuapp.com/gimme",
            "https://meme-api.com/gimme", 
            "https://api.reddit.com/r/memes/hot.json?limit=50",
            "https://meme-api.herokuapp.com/gimme/memes",
            "https://meme-api.herokuapp.com/gimme/dankmemes",
            "https://meme-api.herokuapp.com/gimme/wholesomememes",
            "https://meme-api.herokuapp.com/gimme/me_irl",
            "https://meme-api.herokuapp.com/gimme/ProgrammerHumor"
        ]
        
        # Українські підписи за часом дня
        self.time_based_captions = {
            'morning': [
                "🌅 Коли прокинувся і зрозумів, що сьогодні не вихідний:",
                "☕ Ранкова кава і мем - єдине що тримає на плаву",
                "🐕 Поки ти спав, Бобік готував щось смішне",
                "🌞 Ранок понеділка vs твій настрій:"
            ],
            'work': [
                "💻 Коли бос питає про дедлайн, а ти ще не починав:",
                "📱 Перерва на мем серед робочого хаосу",
                "🤔 Коли робиш вигляд, що працюєш:",
                "💼 Робочі будні vs реальність:",
                "⌨️ Код-рев'ю vs мої очікування:"
            ],
            'lunch': [
                "🍔 Обідня перерва - священний час кожного працівника",
                "🥪 Коли їси і дивишся меми одночасно",
                "😋 Їжа смачніша під мемчики від Бобіка",
                "🍕 Обід в офісі vs обід вдома:"
            ],
            'evening': [
                "🏠 Нарешті дома! Час для якісних мемів",
                "🛋️ Після роботи тільки диван і мемаси",
                "📺 Коли вибираєш між серіалом і мемами:",
                "🌆 Кінець робочого дня - почалося життя"
            ],
            'night': [
                "🌙 О 23:00: 'Ще один мемчик і спати'",
                "🦉 Нічний скрол мемів - моя суперсила",
                "📱 Коли мав лягти спати 2 години тому:",
                "⭐ Нічний Telegram серфінг в дії"
            ]
        }
        
        # Українські хештеги
        self.trending_hashtags = [
            "#мемчик", "#гумор", "#релейтабл", "#настрій", 
            "#життя", "#робота", "#понеділок", "#кава",
            "#україна", "#бобік", "#смішно", "#мемас"
        ]

    def get_time_category(self, hour: int) -> str:
        """Визначає категорію часу для підбору підписів (з урахуванням київського часу)"""
        # Конвертуємо UTC в київський час (+2)
        kyiv_hour = (hour + 2) % 24
        
        if 5 <= kyiv_hour < 10:
            return 'morning'
        elif 10 <= kyiv_hour < 14:
            return 'work'
        elif 14 <= kyiv_hour < 17:
            return 'lunch'
        elif 17 <= kyiv_hour < 22:
            return 'evening'
        else:
            return 'night'

    def localize_meme_with_ai(self, meme_title: str) -> str:
        """Локалізує мем через ChatGPT"""
        if not self.openai_client or not meme_title:
            return meme_title
            
        # Перевіряємо чи текст вже українською
        ukrainian_chars = 'абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'
        ukrainian_count = sum(1 for char in meme_title.lower() if char in ukrainian_chars)
        total_alpha = len([char for char in meme_title.lower() if char.isalpha()])
        
        if total_alpha > 0 and ukrainian_count / total_alpha > 0.3:
            return meme_title  # Вже українською
            
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": f"Адаптуй цей мем для української IT аудиторії 16-35 років, зберігши гумор та суть:\n\n'{meme_title}'\n\nПереклади на українську та заміни незрозумілі американські посилання на українські аналоги. Максимум 100 символів, без емодзі."
                }],
                max_tokens=120,
                temperature=0.7
            )
            
            localized = response.choices[0].message.content.strip()
            localized = localized.replace('"', '').strip()
            
            if localized and len(localized) > 10:
                self.stats['localized_posts'] += 1
                logger.info(f"🇺🇦 Локалізовано: {meme_title[:30]}... → {localized[:30]}...")
                return localized
                
        except Exception as e:
            logger.error(f"❌ AI локалізація помилка: {e}")
            
        return meme_title

    def get_meme(self) -> Optional[Dict]:
        """Отримує мем з множинних джерел з відмовостійкістю"""
        
        # Перемішуємо джерела для різноманітності
        sources = self.meme_sources.copy()
        random.shuffle(sources)
        
        for api_url in sources:
            try:
                logger.info(f"🔍 Спробую API: {api_url}")
                
                headers = {'User-Agent': 'BobikBot/2.0 (Ukrainian Meme Bot)'}
                response = requests.get(api_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'reddit.com' in api_url:
                        # Reddit API format
                        posts = data.get('data', {}).get('children', [])
                        for post in posts[:10]:  # Перевіряємо топ 10
                            post_data = post.get('data', {})
                            if self.is_quality_meme(post_data):
                                return {
                                    'url': post_data.get('url'),
                                    'title': post_data.get('title', ''),
                                    'score': post_data.get('score', 0),
                                    'source': 'reddit'
                                }
                    else:
                        # Meme API format
                        if self.is_quality_meme(data):
                            return {
                                'url': data.get('url'),
                                'title': data.get('title', 'Мем'),
                                'score': data.get('ups', 100),
                                'source': 'meme-api'
                            }
                            
            except Exception as e:
                logger.error(f"❌ API {api_url} помилка: {e}")
                continue
        
        # Fallback мем якщо всі API недоступні
        logger.warning("🆘 Всі API недоступні, використовую fallback")
        return {
            'url': 'https://i.imgflip.com/1bij.jpg',
            'title': 'Success Kid - коли всі API впали, але Бобік не здається!',
            'score': 9999,
            'source': 'fallback'
        }

    def is_quality_meme(self, data: Dict) -> bool:
        """Перевіряє якість мему"""
        try:
            url = data.get('url', '')
            title = data.get('title', '').lower()
            score = data.get('score', data.get('ups', 0))
            
            # Перевірка формату зображення
            if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', 'i.redd.it', 'i.imgur.com']):
                return False
            
            # Мінімальний рейтинг
            if score < 50:
                return False
            
            # Фільтр неприйнятного контенту
            blacklist = ['nsfw', 'porn', 'sex', 'nude', 'politics']
            if any(word in title for word in blacklist):
                return False
            
            # Перевірка дублікатів (простий варіант)
            if url in self.stats['posted_memes']:
                return False
                
            return True
            
        except Exception:
            return False

    def generate_smart_caption(self, meme_data: Dict) -> str:
        """Генерує розумні підписи з AI локалізацією"""
        
        current_hour = datetime.now().hour
        time_category = self.get_time_category(current_hour)
        
        # Вибираємо підпис за часом дня
        time_caption = random.choice(self.time_based_captions[time_category])
        
        # Обробляємо назву мему
        title = meme_data.get('title', '')
        
        # AI локалізація якщо доступна
        if self.openai_client and title:
            title = self.localize_meme_with_ai(title)
        
        # Генеруємо хештеги
        hashtags = random.sample(self.trending_hashtags, 2)
        hashtag_str = ' '.join(hashtags)
        
        # Формуємо фінальний підпис
        ai_marker = " 🤖" if meme_data.get('source') != 'fallback' and self.openai_client else ""
        
        caption = f"{time_caption}\n\n💭 {title}{ai_marker}\n\n📊 Популярність: {meme_data.get('score', 0)}\n🔗 Джерело: {meme_data.get('source', 'unknown')}\n\n{hashtag_str}"
        
        return caption

    async def post_meme_to_channel(self) -> bool:
        """Публікує мем в канал"""
        try:
            meme = self.get_meme()
            if not meme:
                logger.error("❌ Не вдалося отримати мем")
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
            self.stats['posted_memes'].add(meme['url'])
            
            # Очищуємо історію якщо забагато
            if len(self.stats['posted_memes']) > 500:
                self.stats['posted_memes'] = set(list(self.stats['posted_memes'])[-250:])
            
            logger.info(f"✅ Мем опубліковано! ID: {result.message_id}, AI: {'Так' if self.openai_client else 'Ні'}")
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
        logger.info("🕐 Планувальник запущений!")
        logger.info(f"📅 Розклад: {len(self.posting_schedule)} публікацій на день")
        logger.info(f"🤖 AI статус: {'✅ Активний' if self.openai_client else '❌ Вимкнений'}")
        
        while self.scheduler_running:
            try:
                if self.should_post_now():
                    kyiv_time = (datetime.now().hour + 2) % 24
                    logger.info(f"⏰ Час публікації: {datetime.now().strftime('%H:%M')} UTC (Київ: {kyiv_time:02d}:{datetime.now().minute:02d})")
                    
                    success = await self.post_meme_to_channel()
                    if success:
                        logger.info("✅ Автоматична публікація успішна")
                    
                    # Чекаємо 70 секунд щоб не повторювати
                    await asyncio.sleep(70)
                else:
                    # Перевіряємо кожні 30 секунд
                    await asyncio.sleep(30)
                    
            except Exception as e:
                logger.error(f"❌ Помилка в планувальнику: {e}")
                await asyncio.sleep(60)

    def start_scheduler(self):
        """Запуск планувальника"""
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

    def create_main_menu(self) -> InlineKeyboardMarkup:
        """Створює головне меню"""
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
                InlineKeyboardButton("🤖 AI Статус", callback_data="ai_status")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def button_callback(self, update, context):
        """Обробник кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "test_post":
            await query.edit_message_text("🧪 Публікую тестовий мем з AI обробкою...")
            success = await self.post_meme_to_channel()
            
            text = "✅ **Тестовий мем опубліковано!**\n\n" if success else "❌ **Помилка публікації**\n\n"
            text += f"🤖 AI локалізація: {'✅ Активна' if self.openai_client else '❌ Вимкнена'}\n"
            text += f"📊 Локалізовано постів: {self.stats['localized_posts']}\n\n"
            text += "Перевірте канал @BobikFun"
                
            await query.edit_message_text(text, parse_mode='Markdown')
            
        elif query.data == "ai_status":
            if self.openai_client:
                ai_text = f"🤖 **AI Статус: ✅ АКТИВНИЙ**\n\n"
                ai_text += f"📊 **Локалізовано постів**: {self.stats['localized_posts']}\n"
                ai_text += f"🎯 **Функції**: Автоматична українізація мемів\n"
                ai_text += f"🧠 **Модель**: GPT-3.5-turbo\n\n"
                ai_text += "💡 **AI допомагає:**\n"
                ai_text += "• Перекладати англійські меми українською\n"
                ai_text += "• Адаптувати культурні посилання\n"
                ai_text += "• Покращувати зрозумілість для українців"
            else:
                ai_text = "🤖 **AI Статус: ❌ НЕАКТИВНИЙ**\n\n"
                ai_text += "🔑 **Потрібно**: OPENAI_API_KEY в Railway\n"
                ai_text += "⚡ **Поточний режим**: Базова локалізація\n\n"
                ai_text += "**Для активації AI:**\n"
                ai_text += "1. Отримайте ключ: platform.openai.com/api-keys\n"
                ai_text += "2. Додайте в Railway Variables\n"
                ai_text += "3. Перезапустіть бота"
                
            await query.edit_message_text(ai_text, parse_mode='Markdown')
            
        elif query.data == "analytics":
            success_rate = 0
            if self.stats['successful_posts'] + self.stats['failed_posts'] > 0:
                success_rate = (self.stats['successful_posts'] / 
                              (self.stats['successful_posts'] + self.stats['failed_posts']) * 100)
            
            analytics = f"📊 **Аналітика Бобіка 2.0:**\n\n"
            analytics += f"📈 **Постів сьогодні**: {self.stats['posts_today']}/11\n"
            analytics += f"📊 **Всього постів**: {self.stats['total_posts']}\n"
            analytics += f"✅ **Успішних**: {self.stats['successful_posts']}\n"
            analytics += f"❌ **Невдалих**: {self.stats['failed_posts']}\n"
            analytics += f"🎯 **Успішність**: {success_rate:.1f}%\n\n"
            analytics += f"🤖 **AI метрики:**\n"
            analytics += f"• Локалізовано: {self.stats['localized_posts']} постів\n"
            analytics += f"• AI статус: {'✅ Активний' if self.openai_client else '❌ Вимкнений'}\n\n"
            analytics += f"⏰ **Останній пост**: {self.stats['last_post_time'] or 'Ще не було'}\n"
            analytics += f"📅 **Розклад**: {len(self.posting_schedule)} публікацій/день"
            
            await query.edit_message_text(analytics, parse_mode='Markdown')

    async def start_command(self, update, context):
        await update.message.reply_text(
            "🐕 **Привіт! Я Бобік 2.0 з AI локалізацією!**\n\n"
            "🚀 **Нові можливості:**\n"
            f"• 🤖 AI локалізація: {'✅ Активна' if self.openai_client else '❌ Потрібен API ключ'}\n"
            "• 📡 8+ джерел мемів з відмовостійкістю\n"
            "• 🇺🇦 Адаптовано під український час (UTC+2)\n"
            "• 📊 Покращена аналітика\n"
            "• 🎯 11 автопостів на день\n\n"
            "🔗 **Канал:** @BobikFun\n\n"
            "Використовуйте меню нижче:",
            reply_markup=self.create_main_menu(),
            parse_mode='Markdown'
        )

def main():
    """Головна функція"""
    bot = AdvancedBobikBot()
    
    # Створюємо додаток
    application = Application.builder().token(bot.bot_token).build()
    
    # Додаємо обробники
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Запускаємо планувальник
    bot.start_scheduler()
    
    logger.info("🚀 Бобік 2.0 з AI локалізацією запущений!")
    logger.info(f"🤖 AI статус: {'✅ Активний' if bot.openai_client else '⚠️ Базовий режим'}")
    logger.info(f"📅 Розклад: {len(bot.posting_schedule)} публікацій на день")
    logger.info("🇺🇦 Оптимізовано для української аудиторії!")
    
    # Запускаємо бота
    application.run_polling()

if __name__ == "__main__":
    main()
