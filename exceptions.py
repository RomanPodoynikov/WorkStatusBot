class StatusCodeHTTPIsIncorrect(Exception):
    """
    Запрос к эндпоинту API-сервиса не выполнен.
    Код состояния HTTP не 200 ОК.
    """

    pass


class StatusUnknown(Exception):
    """Неизвестный статус домашнего задания."""

    pass


class StatusInDictIsNotAvailable(Exception):
    """В ответе в словаре отсутствует статус домашнего задания."""

    pass
