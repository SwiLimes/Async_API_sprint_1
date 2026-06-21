import abc
import copy
import json
import os
from typing import Any, Dict


class BaseStorage(abc.ABC):
    """Абстрактное хранилище состояния.

    Позволяет сохранять и получать состояние.
    Способ хранения состояния может варьироваться в зависимости
    от итоговой реализации. Например, можно хранить информацию
    в базе данных или в распределённом файловом хранилище.
    """

    @abc.abstractmethod
    def save_state(self, state: Dict[str, Any]) -> None:
        """Сохранить состояние в хранилище."""

    @abc.abstractmethod
    def retrieve_state(self) -> Dict[str, Any]:
        """Получить состояние из хранилища."""


class JsonFileStorage(BaseStorage):
    """Реализация хранилища, использующего локальный файл.

    Формат хранения: JSON
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        if os.path.isfile(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as file:
                self.state = json.loads(file.read())
        else:
            self.state = dict()

    def save_state(self, state: Dict[str, Any]) -> None:
        """Сохранить состояние в хранилище."""
        for key in state.keys():
            self.state[key] = state[key]
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(self.state))

    def retrieve_state(self) -> Dict[str, Any]:
        """Получить состояние из хранилища."""
        if os.path.isfile(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as file:
                self.state = json.loads(file.read())
        return copy.deepcopy(self.state)


class State:
    """Класс для работы с состояниями."""

    def __init__(self, storage: BaseStorage) -> None:
        self.storage = storage

    def set_state(self, key: str, value: Any) -> None:
        """Установить состояние для определённого ключа."""
        state = self.storage.retrieve_state()
        state[key] = value
        self.storage.save_state(state)


    def get_state(self, key: str) -> Any:
        """Получить состояние по определённому ключу."""
        state = self.storage.retrieve_state()
        return state.get(key)
