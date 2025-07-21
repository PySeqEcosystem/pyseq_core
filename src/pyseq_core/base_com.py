from abc import ABC, abstractmethod
from typing import Union
from attrs import define, field
import asyncio


@define
class BaseCOM(ABC):
    address: str = field()
    lock: asyncio.Lock = field(factory=asyncio.Lock)
    """
    Abstract base class for communication interfaces.

    Attributes:
        address (str): The address of the communication interface.
        lock (asyncio.Lock): An asyncio lock to ensure thread-safe access to the interface.
    """

    @abstractmethod
    async def connect(self) -> Union[str, None]:
        """
        Asynchronously establishes a connection to the communication interface.

        Returns:
            str: Message if the connection is successful or already exists, otherwise None.
        """
        async with self.lock:
            pass

    @abstractmethod
    async def command(self, command: str) -> Union[str, dict]:
        """
        Asynchronously sends a command to the communication interface.

        Args:
            command (str): The command string to be sent.
        """
        async with self.lock:
            pass

    @abstractmethod
    async def close(self) -> bool:
        """
        Asynchronously closee a connection to the communication interface.

        Returns:
            bool: True if the connection is gracefully closed, otherwise False.
        """
        async with self.lock:
            pass
