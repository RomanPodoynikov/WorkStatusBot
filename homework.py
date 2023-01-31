import logging
import requests
import telegram
import time

from dotenv import load_dotenv
from exceptions import (StatusCodeHTTPIsIncorrect, StatusUnknown,
                        StatusInDictIsNotAvailable, MessageNotSent)
from http import HTTPStatus
from os import getenv
from sys import exit

load_dotenv()

PRACTICUM_TOKEN = getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
)


def check_tokens():
    """Проверяет доступность необходимых переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for key, value in tokens.items():
        if value is None:
            logging.critical(f'Отсутствует переменная окружения: {key}. '
                             'Программа принудительно остановлена.')
            exit(0)
    logging.info('Переменные окружения доступны.')
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение "{message}".')
    except telegram.error.TelegramError as error:
        logging.error(f'Не удается отправить сообщение. Ошибка - {error}')
        raise MessageNotSent


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        params = {'from_date': {timestamp}}
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        if response.status_code == HTTPStatus.OK:
            logging.info(f'Запрос к {ENDPOINT} выполнен.')
            return response.json()
        logging.error('Код состояния HTTP отличен от 200 ОК. '
                      f'Код состояния - {response.status_code}.')
        raise StatusCodeHTTPIsIncorrect
    except Exception as error:
        logging.error(error, f'Запрос к {ENDPOINT} не выполнен.')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        if isinstance(response,
                      dict) and isinstance(response.get('homeworks'), list):
            homework = response.get('homeworks')
            logging.info('Проверка ответа API выполнена успешно.')
            return homework
        raise TypeError
    except TypeError as error:
        logging.error(error, 'Отсутствие ожидаемых ключей в ответе API.')
    except Exception as error:
        logging.error(error, 'Проверка ответа API не выполнена.')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None:
        raise StatusInDictIsNotAvailable
    elif status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS.get(status)
        logging.info(f'Извлечен статус "{status}" домашней работы.')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise StatusUnknown


def main():
    """Основная логика работы бота."""
    logging.info('Запуск работы бота.')
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - RETRY_PERIOD
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            number_of_hw = len(homework)
            if number_of_hw > 0:
                message = parse_status(homework[0])
            else:
                message = 'Новые статусы работы отсутствуют.'
                logging.debug('Новые статусы работы отсутствуют.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}.'
            logging.error(f'Сбой в работе программы: {error}.')
        finally:
            send_message(bot, message)
            logging.info('Перезапуск работы бота.')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
