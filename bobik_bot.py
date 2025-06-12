import requests
import asyncio
import random
import logging
import json
import time
from datetime import datetime, timedelta
from telegram import Bot
from telegram.ext import Application, CommandHandler
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
        
        # Тренди українських підписів за часом дня
        self.time_based_captions = {
            'morning': [
                "🌅 Доброго ранку! Бобік приніс ранковий заряд позитиву!",
                "☕ Ранкова порція гумору від Бобіка!",
                "🐕 Прокидайся! Бобік знайшов щось веселе!",
                "🌞 Сонячний ранок + смішний мем = ідеальний день!"
            ],
            'work': [
                "💼 Робочі будні? Бобік допоможе!",
                "⚡ Заряд енергії для продуктивного дня!",
                "🎯 Бобік знає як підняти настрій на роботі!",
                "💪 Мотивація від Бобіка для робочого дня!"
            ],
            'lunch': [
                "🍽️ Обідня перерва з Бобіком!",
                "😋 Смачного + смішного від Бобіка!",
                "🥙 Час обіду = час для мемів!",
                "🍕 Бобік підготував десерт для твого обіду!"
            ],
            'evening': [
                "🏠 Кінець робочого дня! Час розслабитися з Бобіком!",
                "🌆 Вечірня порція гумору від Бобіка!",
                "🛋️ Час чілити з мемами від Бобіка!",
                "🎬 Вечірнє шоу від Бобіка починається!"
            ],
            'night': [
                "🌙 Нічні сови, це для вас!",
                "🦉 Бобік не спить - розважає нічних мандрівників!",
                "⭐ Зіркова ніч + мем від Бобіка = ідеально!",
                "🌃 Нічний гумор від безсонного Бобіка!"
            ]
        }
        
        # Тренди та хештеги
        self.trending_hashtags = [
            "#мем", "#гумор", "#Україна", "#настрій", 
            "#сміх", "#позитив", "#Бобік", "#мемUA"
        ]
        
        self.scheduler_running = False

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
        
        # Додаємо контекст з назви мему
        title = meme_data.get('title', '')
        
        # Генеруємо хештеги
        hashtags = random.sample(self.trending_hashtags, 2)
        hashtag_str = ' '.join(hashtags)
        
        # Формуємо фінальний підпис
        caption = f"{time_caption}\n\n💭 {title}\n\n{hashtag_str}"
        
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
        self.scheduler_running = False
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
            "🐕 Привіт! Я покращений Бобік!\n\n"
            "🚀 **Нові можливості:**\n"
            "• 11 автопостів на день\n"
            "• Розумні підписи за часом\n"
            "• Покращена аналітика\n"
            "• Множинні джерела мемів\n\n"
            "📱 **Команди:**\n"
            "/meme - отримати мем\n"
            "/test - опублікувати в канал\n"
            "/analytics - детальна статистика\n"
            "/schedule - управління розкладом\n"
            "/status - поточний статус",
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
    """Головна функція з автоматичним розкладом"""
    bot = AdvancedBobikBot()
    
    # Створюємо додаток
    application = Application.builder().token(bot.bot_token).build()
    
    # Додаємо команди
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("meme", bot.meme_command))
    application.add_handler(CommandHandler("test", bot.test_command))
    application.add_handler(CommandHandler("analytics", bot.analytics_command))
    application.add_handler(CommandHandler("schedule", bot.schedule_command))
    application.add_handler(CommandHandler("status", bot.status_command))
    
    # ЗАПУСКАЄМО АВТОМАТИЧНИЙ ПЛАНУВАЛЬНИК
    bot.start_scheduler()
    
    logger.info("🚀 Покращений Бобік запущений з автоматичним розкладом!")
    logger.info(f"📅 Буде публікувати {len(bot.posting_schedule)} мемів на день")
    
    # Запускаємо бота
    application.run_polling()

if __name__ == "__main__":
    main()
