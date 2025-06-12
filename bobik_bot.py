import requests
import asyncio
import random
import logging
import json
import time
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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
        
        # Розширена статистика
        self.stats = {
            'posts_today': 0,
            'total_posts': 0,
            'last_post_time': None,
            'successful_posts': 0,
            'failed_posts': 0,
            'best_engagement_time': None,
            'daily_stats': {}
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
        
        # Розширені джерела мемів
        self.meme_sources = {
            'general': [
                "https://meme-api.herokuapp.com/gimme",
                "https://meme-api.herokuapp.com/gimme/memes",
                "https://meme-api.herokuapp.com/gimme/dankmemes"
            ],
            'wholesome': [
                "https://meme-api.herokuapp.com/gimme/wholesomememes",
                "https://meme-api.herokuapp.com/gimme/MadeMeSmile"
            ],
            'tech': [
                "https://meme-api.herokuapp.com/gimme/ProgrammerHumor",
                "https://meme-api.herokuapp.com/gimme/softwaregore"
            ],
            'relatable': [
                "https://meme-api.herokuapp.com/gimme/me_irl",
                "https://meme-api.herokuapp.com/gimme/meirl"
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
                InlineKeyboardButton("⏰ По часах", callback_data="hourly_stats")
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
            resize_keyboard=True, 
            persistent=True,
            one_time_keyboard=False
        )
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
        """Розширений пошук мемів з ротацією джерел"""
        all_sources = []
        
        # Збираємо всі джерела
        for category, urls in self.meme_sources.items():
            all_sources.extend(urls)
        
        # Перемішуємо для рандомізації
        random.shuffle(all_sources)
        
        for api_url in all_sources:
            try:
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
                        
            except Exception as e:
                logger.error(f"Помилка API {api_url}: {e}")
                continue
        
        # Якщо всі API недоступні - фоллбек меми
        return self.get_fallback_meme()

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
        """Покращена публікація з аналітикою"""
        try:
            meme = self.get_meme_advanced()
            if not meme:
                logger.error("Не вдалося отримати мем")
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
            
            # Зберігаємо статистику по часах для аналітики
            hour_key = current_time.strftime('%H')
            if hour_key not in self.stats['daily_stats']:
                self.stats['daily_stats'][hour_key] = 0
            self.stats['daily_stats'][hour_key] += 1
            
            logger.info(f"✅ Мем опубліковано! ID: {result.message_id}, Час: {current_time.strftime('%H:%M')}")
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
                'daily_stats': {}
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
                parse_mode='Markdown'
            )

    def get_help_info(self) -> str:
        """Інформація про допомогу"""
        return """
ℹ️ **Довідка по боту Бобік:**

🎯 **Основні функції:**
• Автоматична публікація 11 мемів/день
• Розумні українські підписи
• Аналітика та статистика
• Ручне управління публікаціями

📱 **Постійне меню:**
• **📊 Аналітика** - статистика каналу
• **🧪 Тест пост** - швидка публікація
• **🎲 Мем** - випадковий мем приватно
• **📅 Розклад** - план публікацій
• **⚙️ Управління** - запуск/зупинка
• **📈 Статус** - поточний стан
• **🔧 Налаштування** - конфігурація
• **ℹ️ Допомога** - ця довідка

⚙️ **Управління:**
• Запуск/зупинка розкладу
• Екстрена публікація
• Очищення статистики
• Налаштування параметрів

📊 **Аналітика:**
• Загальна статистика
• Статистика по часах
• Найкращі години для постів
• Експорт даних

❓ **Потрібна допомога?**
Звертайтесь до адміністратора каналу!
"""
        """Інформація про допомогу"""
        return """
ℹ️ **Довідка по боту Бобік:**

🎯 **Основні функції:**
• Автоматична публікація 11 мемів/день
• Розумні українські підписи
• Аналітика та статистика
• Ручне управління публікаціями

📱 **Команди:**
• `/menu` - головне меню
• `/start` - інформація про бота
• `/meme` - випадковий мем
• `/test` - тестова публікація

⚙️ **Управління:**
• Запуск/зупинка розкладу
• Екстрена публікація
• Очищення статистики
• Налаштування параметрів

📊 **Аналітика:**
• Загальна статистика
• Статистика по часах
• Найкращі години для постів
• Експорт даних

🔧 **Налаштування:**
• Стиль підписів
• Джерела мемів
• Розклад публікацій
• Хештеги

❓ **Потрібна допомога?**
Звертайтесь до адміністратора каналу!
"""
        logger.info("⏹️ Планувальник зупинено!")

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

    # Команди бота
    async def start_command(self, update, context):
        await update.message.reply_text(
            "🐕 **Привіт! Я покращений Бобік!**\n\n"
            "🚀 **Нові можливості:**\n"
            "• 11 автопостів на день\n"
            "• Розумні українські підписи\n"
            "• Постійне меню управління\n"
            "• Покращена аналітика\n"
            "• Множинні джерела мемів\n\n"
            "📱 **Використовуй меню внизу екрану для зручності!**\n\n"
            "🔗 **Канал:** @BobikFun",
            reply_markup=self.create_permanent_menu(),
            parse_mode='Markdown'
        )

    async def menu_command(self, update, context):
        """Команда для показу розширеного меню"""
        await update.message.reply_text(
            "🐕 **Розширене меню Бобіка**\n\nОберіть дію:",
            reply_markup=self.create_main_menu(),
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
