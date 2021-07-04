
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram.ext import CommandHandler, Updater

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
URL = 'https://bash.im/'
URL_RAND = 'https://bash.im/random'

# Формат часа от 0 до 23
BOT_TIME_START = int(10)
BOT_TIME_END = int(22)

last_quote_number = 0
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# здесь мы задаем глобальную конфигурацию для всех логеров
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)

# а тут настраиваем логгер для текущего файла .py
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
file_handler = RotatingFileHandler('main.log', maxBytes=50000000,
                                   backupCount=5)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


def request_site(url):
    """Запрашиваем данные с www.bash.im"""
    logging.debug('Запрашиваем данные с www.bash.im')
    try:
        response = requests.get(url)
        return response.text

    except requests.exceptions.RequestException as e:
        logging.error(f'Не удалось получить данные с www.bash.im: {e}')
        raise requests.exceptions.RequestException(
            f'Не удалось получить данные с www.bash.im: {e}')


def find_new_quotes(quotes):
    """Ищем новые цитаты"""
    logging.debug('Ищем новые цитаты')
    global last_quote_number
    greater_quotes_num = list(quotes)[0]
    lower_quotes_num = list(quotes)[-1]
    if not last_quote_number:
        last_quote_number = lower_quotes_num

    new_quotes = {}
    for quote_num, quote_text in quotes.items():
        if quote_num > last_quote_number:
            new_quotes[quote_num] = quote_text
    last_quote_number = greater_quotes_num
    return new_quotes


def parse_quotes(raw_text):
    """Парсим цитаты с www.bash.im"""
    logging.debug('Парсим цитаты')
    try:
        data = BeautifulSoup(raw_text, features='html.parser')
        quotes = data.find_all('div', class_='quote__frame')
        all_quotes = {}
        for quote in quotes:
            quote_number = quote.find('a',
                                      class_='quote__header_permalink').text
            quote_number = int(quote_number.replace('#', ''))
            quote_text = quote.find('div',
                                    class_='quote__body').get_text().strip()
            all_quotes[quote_number] = quote_text
        return all_quotes

    except Exception as e:
        logging.error(f'Не удалось распарсить цитаты: {e}')
        raise Exception(
            f'Не удалось распарсить цитаты: {e}')


def send_message(message):
    """Функция бота для отправки сообщения в чат"""
    logging.info('Сообщение отправлено')
    return bot.send_message(CHAT_ID, message)


def main():
    logging.debug('Запущен главный цикл бота')
    while True:
        if not working_time():
            logging.info('Не время для работы')
            time.sleep(60 * 60)  # Перерыв на 1 час
            continue

        try:
            response = request_site(URL)
            quotes = parse_quotes(response)
            if not quotes:
                logging.debug('Нет новых цитат')
                time.sleep(5 * 60)  # Опрашивать раз в пять минут
                continue

            new_quotes = find_new_quotes(quotes)
            if not new_quotes:
                logging.debug('Нет новых цитат')
                time.sleep(5 * 60)  # Опрашивать раз в пять минут
                continue

            for value in new_quotes.values():
                send_message(value)
            time.sleep(5 * 60)  # Опрашивать раз в пять минут

        except Exception as e:
            print(f'Бот упал с ошибкой: {e}')
            logging.error(f'Бот упал с ошибкой: {e}')
            send_message(f'Бот упал с ошибкой: {e}')
            time.sleep(5 * 60)


def get_rand_quotes():
    """Получаем случайные цитаты"""
    logging.debug('Получаем случайные цитаты')
    while True:
        try:
            response = request_site(URL_RAND)
            quotes = parse_quotes(response)
            return quotes

        except Exception as e:
            print(f'Бот упал с ошибкой: {e}')
            logging.error(f'Бот упал с ошибкой: {e}')
            send_message(f'Бот упал с ошибкой: {e}')


def rand_quotes(update, context):
    """После команды /rand отправляет случайные цитаты"""
    logging.debug('Отправляем случайные цитаты')
    chat = update.effective_chat
    quotes = get_rand_quotes()
    if quotes:
        logging.info('Сообщение отправлено')
        context.bot.send_message(chat_id=chat.id, text='Случайные цитаты')
        for value in quotes.values():
            send_message(value)
    else:
        logging.info('Сообщение отправлено')
        context.bot.send_message(chat_id=chat.id, text='Ой, цитаты кончились!')


def test():
    global last_quote_number
    last_quote_number = 0
    site = (
        '<div class="quote__frame">',
        '<a class="quote__header_permalink" href="/quote/002">#302</a>',
        '<div class="quote__body">Цитата 2</div>', '</div>',
        '<div class="quote__frame">',
        '<a class="quote__header_permalink" href="/quote/002">#301</a>',
        '<div class="quote__body">Цитата 1</div>', '</div>'
        '<div class="quote__frame">',
        '<a class="quote__header_permalink" href="/quote/002">#300</a>',
        '<div class="quote__body">Цитата 0</div>', '</div>'
    )
    quotes = parse_quotes(str(site))
    new_quotes = find_new_quotes(quotes)
    for key, value in new_quotes.items():
        send_message(value)


def working_time():
    """Определяем может ли бот отправлять сообщения в это время"""
    time_now = time.localtime()
    if BOT_TIME_END > time_now.tm_hour > BOT_TIME_START:
        return True

    return False


def wake_up(update, context):
    """Сообщение при запуске бота"""
    logging.debug('Отправляем сообщение при запуске бота')
    chat = update.effective_chat
    text = 'Бот для получения новых цитат с bash.im запущен!'
    context.bot.send_message(chat_id=chat.id, text=text)


def help_cmd(update, context):
    """Сообщение после команды /help"""
    logging.debug('Отправляем сообщение после команды /help')
    chat = update.effective_chat
    text = 'Бот автоматически отправляет новые цитаты.'
    text += ' Для получения случайных цитат отправьте /rand'
    context.bot.send_message(chat_id=chat.id, text=text)


if __name__ == '__main__':
    logging.debug('Бот запущен')
    updater = Updater(token=TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.dispatcher.add_handler(CommandHandler('help', help_cmd))
    updater.dispatcher.add_handler(CommandHandler('rand', rand_quotes))
    updater.start_polling()

    # last_quote_number = 466161
    main()
    # test()
