import logging
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
from os import getenv
from sys import exit, stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (StatusCodeHTTPIsIncorrect, StatusUnknown,
                        StatusInDictIsNotAvailable)

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('program.log',
                              maxBytes=50000000,
                              backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


def check_tokens():
    """Проверяет доступность необходимых переменных окружения."""
    logger.info('Начало проверки доступности переменных окружения.')
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    empty_tokens = []
    for key, value in tokens.items():
        if value is None:
            empty_tokens.append(key)
    if empty_tokens != []:
        for i in empty_tokens:
            logger.critical(f'Отсутствует переменная окружения: {i}.')
        exit('Программа принудительно остановлена.')
    logger.debug('Переменные окружения доступны.')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logger.info('Начало отправки сообщения.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logger.error(f'Не удается отправить сообщение - {error}')
    logger.debug(f'Бот отправил сообщение "{message}".')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    logger.info('Начало запроса к эндпоинту API-сервиса.')
    try:
        params = {'from_date': {timestamp}}
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
    except requests.RequestException as error:
        raise ConnectionError(f'Запрос к {ENDPOINT} не выполнен - {error}')
    if response.status_code == HTTPStatus.OK:
        logger.debug(f'Запрос к {ENDPOINT} выполнен успешно.')
        return response.json()
    raise StatusCodeHTTPIsIncorrect('Код состояния HTTP отличен от 200 ОК. '
                                    f'Код состояния - {response.status_code}.')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    logger.info('Начало проверки ответа API.')
    homeworks = 'homeworks'
    current_date = 'current_date'
    if not isinstance(response, dict):
        raise TypeError('Ответ API пришел не в виде словаря.')
    if homeworks not in response:
        raise KeyError(f'Отсутствие ключа {homeworks} в ответе API.')
    if current_date not in response:
        raise KeyError(f'Отсутствие ключа {current_date} в ответе API.')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(f'Значением в ключе {homeworks} является не список.')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    logger.info('Начало извлечения статуса домашней работы.')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None:
        raise StatusInDictIsNotAvailable('Отсутствует статус домашней работы.')
    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS.get(status)
        logger.info(f'Извлечен статус "{status}" домашней работы.')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise StatusUnknown('Неизвестный статус домашней работы.')


def main():
    """Основная логика работы бота."""
    logger.info('Запуск работы бота.')
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_report = dict(name='', output='')
    prev_report = current_report.copy()
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            if homeworks:
                message = parse_status(homeworks[0])
                logger.debug(f'Сообщение "{message}" получено.')
                current_report = dict(name=homeworks[0].get('homework_name'),
                                      output=message)
            else:
                message = 'Новые статусы работы отсутствуют.'
                logger.debug(f'{message}')
                current_report['output'] = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}.'
            logger.error(f'{message}')
            current_report['output'] = message
            print(current_report)
        finally:
            if current_report != prev_report:
                send_message(bot, message)
                prev_report = current_report.copy()
            logger.info('Запущен период ожидания.')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(stdout)]
    )

    main()
