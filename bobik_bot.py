import requests
import asyncio
import random
import logging
from telegram import Bot
from telegram.ext import Application, CommandHandler

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BobikBot:
    def __init__(self):
        self.bot_token = "7882259321:AAGGqql6LD6bzLHTOb1HdKUYs2IJBZqsd6E"
        self.channel_id = "@BobikFun"
        self.stats = {'posts': 0}
        
        # Українські підписи
        self.captions = [
            "🐕 Бобік знайшов щось смішне!",
            "😂 Це треба показати всім!",
            "🔥 Свіжий гумор від Бобіка!",
            "😄 Хороший настрій гарантований!",
            "🎯 Бобік не промахнувся!"
        ]

    def get_meme(self):
        """Отримує мем з різних джерел"""
        # Список API для мемів
        apis = [
            "https://meme-api.herokuapp.com/gimme",
            "https://meme-api.herokuapp.com/gimme/dankmemes", 
            "https://meme-api.herokuapp.com/gimme/memes",
            "https://meme-api.herokuapp.com/gimme/wholesomememes",
            "https://meme-api.herokuapp.com/gimme/ProgrammerHumor"
        ]
        
        for api_url in apis:
            try:
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Перевіряємо чи є URL зображення
                    if data.get('url'):
                        url = data['url']
                        # Перевіряємо формат
                        if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                            # Знижуємо вимоги до upvotes
                            ups = data.get('ups', 0)
                            if ups >= 10:  # Знизив з 100 до 10
                                return {
                                    'url': url,
                                    'title': data.get('title', ''),
                                    'ups': ups
                                }
                            # Якщо upvotes низькі, але мем є - все одно беремо
                            elif url:
                                return {
                                    'url': url,
                                    'title': data.get('title', 'Безназви мем'),
                                    'ups': ups
                                }
                                
            except Exception as e:
                logger.error(f"Помилка API {api_url}: {e}")
                continue
                
        # Якщо жоден API не спрацював - fallback на статичний мем
        logger.warning("Всі API недоступні, використовую fallback мем")
        return {
            'url': 'https://i.imgflip.com/1bij.jpg',  # Знаменитий Success Kid мем
            'title': 'Fallback мем - коли API не працюють!',
            'ups': 9999
        }


    async def start_command(self, update, context):
        """Команда /start"""
        await update.message.reply_text(
            "🐕 Привіт! Я Бобік!\n\n"
            "🎯 Публікую меми в @BobikFun\n\n"
            "Команди:\n"
            "/meme - отримати мем\n"
            "/test - опублікувати в канал\n"
            "/stats - статистика"
        )

    async def meme_command(self, update, context):
        """Команда /meme"""
        await update.message.reply_text("🔍 Шукаю мем...")
        
        meme = self.get_meme()
        if meme:
            caption = f"{random.choice(self.captions)}\n\n💭 {meme['title']}"
            await update.message.reply_photo(photo=meme['url'], caption=caption)
        else:
            await update.message.reply_text("😔 Не знайшов мему, спробуй ще раз!")

    async def test_command(self, update, context):
        """Команда /test - публікація в канал"""
        await update.message.reply_text("🧪 Публікую тестовий мем в канал...")
        
        meme = self.get_meme()
        if not meme:
            await update.message.reply_text("❌ Не знайшов мему!")
            return
            
        try:
            caption = f"{random.choice(self.captions)}\n\n💭 {meme['title']}"
            bot = Bot(token=self.bot_token)
            
            result = await bot.send_photo(
                chat_id=self.channel_id,
                photo=meme['url'],
                caption=caption
            )
            
            self.stats['posts'] += 1
            
            await update.message.reply_text(
                f"✅ Мем опубліковано в канал!\n"
                f"🔗 https://t.me/BobikFun/{result.message_id}"
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка: {str(e)}")

    async def stats_command(self, update, context):
        """Команда /stats"""
        await update.message.reply_text(
            f"📊 Статистика Бобіка:\n"
            f"📈 Опубліковано: {self.stats['posts']}\n"
            f"🔗 Канал: @BobikFun"
        )

def main():
    """Головна функція"""
    bot = BobikBot()
    
    # Створюємо додаток
    application = Application.builder().token(bot.bot_token).build()
    
    # Додаємо команди
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("meme", bot.meme_command))
    application.add_handler(CommandHandler("test", bot.test_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    
    logger.info("🚀 Бобік запущений!")
    
    # Запускаємо бота
    application.run_polling()

if __name__ == "__main__":
    main()
