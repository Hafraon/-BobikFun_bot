import os
import requests
import asyncio
import random
import schedule
import time
from datetime import datetime, timedelta
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from typing import List, Dict, Optional
import json

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BobikMemeBot:
    def __init__(self):
        self.bot_token = "7882259321:AAGGqql6LD6bzLHTOb1HdKUYs2IJBZqsd6E"
        self.channel_id = "@BobikFun"  # Канал для публікації мемів
        self.bot = Bot(token=self.bot_token)
        
        # Безкоштовні API для мемів
        self.meme_sources = {
            'reddit_memes': 'https://meme-api.herokuapp.com/gimme',
            'programming': 'https://meme-api.herokuapp.com/gimme/ProgrammerHumor',
            'wholesome': 'https://meme-api.herokuapp.com/gimme/wholesomememes',
            'dankmemes': 'https://meme-api.herokuapp.com/gimme/dankmemes',
            'ukraininan_context': 'https://meme-api.herokuapp.com/gimme/me_irl'
        }
        
        # Українські фрази для локалізації
        self.ukrainian_captions = [
            "🐕 Бобік знайшов щось смішне!",
            "😂 Це треба показати всім!", 
            "🔥 Свіжий гумор від Бобіка!",
            "😄 Хороший настрій гарантований!",
            "🎯 Бобік не промахнувся!",
            "💎 Золотий мем дня!",
            "⚡ Бобік на зв'язку!",
            "🚀 Заряд позитиву!",
            "🎪 Час сміятися!",
            "🌟 Якість від Бобіка!"
        ]
        
        # Розклад публікацій (UTC)
        self.posting_schedule = [
            "06:00",  # Ранкова порція
            "09:00",  # Робочий день
            "12:00",  # Обід  
            "15:00",  # Після обіду
            "18:00",  # Кінець робочого дня
            "21:00",  # Вечірній релакс
            "23:30"   # Для нічних сов
        ]
        
        # Статистика
        self.stats = {
            'posts_today': 0,
            'total_posts': 0,
            'last_post_time': None
        }

    async def get_meme_from_source(self, source_name: str) -> Optional[Dict]:
        """Отримує мем з конкретного джерела"""
        try:
            url = self.meme_sources.get(source_name)
            if not url:
                return None
                
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Фільтруємо якісні меми
                if self.is_quality_meme(data):
                    return data
                    
        except Exception as e:
            logger.error(f"Помилка отримання мему з {source_name}: {e}")
            
        return None

    def is_quality_meme(self, meme_data: Dict) -> bool:
        """Перевіряє якість мему"""
        try:
            ups = meme_data.get('ups', 0)
            title = meme_data.get('title', '').lower()
            
            # Фільтр якості
            if ups < 100:  # Мінімум 100 upvotes
                return False
                
            # Перевіряємо на неприйнятний контент
            bad_words = ['nsfw', 'politics', 'religion', 'controversial']
            if any(word in title for word in bad_words):
                return False
                
            # Перевіряємо формат зображення
            url = meme_data.get('url', '')
            if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Помилка перевірки якості: {e}")
            return False

    def localize_meme(self, meme_data: Dict) -> Dict:
        """Адаптує мем для української аудиторії"""
        try:
            original_title = meme_data.get('title', '')
            
            # Додаємо український контекст
            ukrainian_caption = random.choice(self.ukrainian_captions)
            
            # Створюємо локалізований пост
            localized = {
                'image_url': meme_data.get('url'),
                'caption': f"{ukrainian_caption}\n\n💭 {original_title}",
                'source_ups': meme_data.get('ups', 0),
                'source': meme_data.get('subreddit', 'Unknown')
            }
            
            return localized
            
        except Exception as e:
            logger.error(f"Помилка локалізації: {e}")
            return meme_data

    async def find_best_meme(self) -> Optional[Dict]:
        """Знаходить найкращий мем з усіх джерел"""
        candidates = []
        
        # Збираємо кандидатів з усіх джерел
        for source_name in self.meme_sources:
            meme = await self.get_meme_from_source(source_name)
            if meme:
                candidates.append((meme, source_name))
                
        if not candidates:
            return None
            
        # Сортуємо за якістю (upvotes)
        candidates.sort(key=lambda x: x[0].get('ups', 0), reverse=True)
        
        # Берємо найкращий
        best_meme, source = candidates[0]
        
        # Локалізуємо
        return self.localize_meme(best_meme)

    async def post_meme_to_channel(self, meme_data: Dict) -> bool:
        """Публікує мем у канал"""
        try:
            image_url = meme_data.get('image_url')
            caption = meme_data.get('caption')
            
            if not image_url:
                return False
                
            # Відправляємо фото з підписом
            await self.bot.send_photo(
                chat_id=self.channel_id,
                photo=image_url,
                caption=caption,
                parse_mode='HTML'
            )
            
            # Оновлюємо статистику
            self.stats['posts_today'] += 1
            self.stats['total_posts'] += 1
            self.stats['last_post_time'] = datetime.now()
            
            logger.info(f"✅ Мем опубліковано! Загалом сьогодні: {self.stats['posts_today']}")
            return True
            
        except Exception as e:
            logger.error(f"Помилка публікації: {e}")
            return False

    async def scheduled_post(self):
        """Планова публікація мему"""
        logger.info("🔍 Шукаю новий мем для публікації...")
        
        meme = await self.find_best_meme()
        if meme:
            success = await self.post_meme_to_channel(meme)
            if success:
                logger.info("🎉 Мем успішно опубліковано!")
            else:
                logger.error("❌ Не вдалося опублікувати мем")
        else:
            logger.warning("⚠️ Не знайдено жодного підходящого мему")

    def setup_scheduler(self):
        """Налаштовує розклад публікацій"""
        for time_str in self.posting_schedule:
            schedule.every().day.at(time_str).do(
                lambda: asyncio.create_task(self.scheduled_post())
            )
        
        logger.info(f"📅 Розклад налаштовано: {len(self.posting_schedule)} публікацій на день")

    async def start_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        await update.message.reply_text(
            "🐕 Привіт! Я Бобік - твій веселий помічник!\n\n"
            "🎯 Моя місія: ділитися найкращими мемами щодня!\n"
            "⏰ Публікую 7 разів на день в [@BobikFun](https://t.me/BobikFun)\n"
            "🔥 Тільки якісний контент з високим рейтингом\n\n"
            "Команди:\n"
            "/stats - статистика\n"
            "/meme - отримати випадковий мем\n"
            "/test - тестова публікація\n"
            "/testchannel - тест підключення до каналу",
            parse_mode='Markdown'
        )

    async def stats_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        stats_text = f"""
📊 **Статистика Бобіка:**

📈 Постів сьогодні: {self.stats['posts_today']}
🎯 Всього постів: {self.stats['total_posts']}
⏰ Останній пост: {self.stats['last_post_time'] or 'Ще не було'}

🕐 Розклад: {len(self.posting_schedule)} разів на день
🎪 Джерел мемів: {len(self.meme_sources)}
🔗 Канал: [@BobikFun](https://t.me/BobikFun)
"""
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    async def meme_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /meme - отримати випадковий мем"""
        await update.message.reply_text("🔍 Бобік шукає смішний мем...")
        
        meme = await self.find_best_meme()
        if meme:
            await update.message.reply_photo(
                photo=meme['image_url'],
                caption=meme['caption']
            )
        else:
            await update.message.reply_text("😔 Бобік не знайшов підходящого мему. Спробуй пізніше!")

    async def test_post_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /test - тестова публікація"""
        await update.message.reply_text("🧪 Тестую публікацію...")
        await self.scheduled_post()
        await update.message.reply_text("✅ Тест завершено!")

    async def test_channel_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /testchannel - тест з'єднання з каналом"""
        test_message = f"🧪 **Тест підключення!**\n\n✅ Бобік успішно підключений до каналу!\n🕐 Час тесту: {datetime.now().strftime('%H:%M:%S')}"
        
        try:
            result = await self.bot.send_message(
                chat_id=self.channel_id,
                text=test_message,
                parse_mode='Markdown'
            )
            
            await update.message.reply_text(
                f"✅ **Успіх!** Тестове повідомлення відправлено!\n"
                f"📊 **Message ID:** {result.message_id}\n"
                f"🆔 **Канал:** {self.channel_id}\n"
                f"🔗 **Перевір:** https://t.me/BobikFun/{result.message_id}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Помилка підключення:**\n\n"
                f"🔍 **Деталі:** `{str(e)}`\n\n"
                f"💡 **Перевір:**\n"
                f"• Бот доданий до каналу?\n"
                f"• Є права на публікацію?\n"
                f"• Channel ID правильний?",
                parse_mode='Markdown'
            )

    def run_scheduler(self):
        """Запуск планувальника"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Перевіряємо кожну хвилину

    async def run_bot(self):
        """Основний цикл бота"""
        # Створюємо додаток
        application = Application.builder().token(self.bot_token).build()
        
        # Додаємо обробники команд
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("meme", self.meme_command))
        application.add_handler(CommandHandler("test", self.test_post_command))
        application.add_handler(CommandHandler("testchannel", self.test_channel_command))
        
        # Налаштовуємо планувальник
        self.setup_scheduler()
        
        logger.info("🚀 Бобік запущений! Готовий до роботи!")
        
        # Запускаємо бота
        await application.run_polling()

# Точка входу
async def main():
    bot = BobikMemeBot()
    await bot.run_bot()

if __name__ == "__main__":
    # Для Railway та інших хостингів
    import threading
    
    bot = BobikMemeBot()
    
    # Запускаємо планувальник в окремому потоці
    scheduler_thread = threading.Thread(target=bot.run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Запускаємо основного бота
    asyncio.run(main())
