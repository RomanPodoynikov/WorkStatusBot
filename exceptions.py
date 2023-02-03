class StatusCodeHTTPIsIncorrect(Exception):
    """
    Запрос к эндпоинту API-сервиса не выполнен.
    Код состояния HTTP не 200 ОК.
    """

    pass


class StatusUnknown(Exception):
    """Неизвестный статус домашнего задания."""

    pass


class NameInDictIsNotAvailable(Exception):
    """В ответе в словаре отсутствует имя домашнего задания."""

    pass
