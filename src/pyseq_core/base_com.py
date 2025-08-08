from abc import ABC, abstractmethod
from typing import Union, Any
from attrs import define, field
import asyncio
import logging
from functools import cached_property

LOGGER = logging.getLogger("PySeq")


@define
class BaseCOM(ABC):
    name: str = field()
    address: str = field()
    config: dict = field()
    lock: asyncio.Lock = field(factory=asyncio.Lock)
    com: Any = field(default=None, init=False)
    _cmdid: int = field(default=0)
    """
    Abstract base class for communication interfaces.

    Attributes:
        name (str): Typically name of the insrument the COM is used with
        address (str): The address of the communication interface.
        config (dict): Settings for communication interface
        lock (asyncio.Lock): An asyncio lock to ensure thread-safe access to the interface.
        com (Any): Actual communication interface
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
        Asynchronously close a connection to the communication interface.

        Returns:
            bool: True if the connection is gracefully closed, otherwise False.
        """
        async with self.lock:
            pass

    def bump_cmdid(self):
        if self._cmdid >= 9999:
            self._cmdid = 0
        self._cmdid += 1
        return f"{self._cmdid:04d}"


@define(kw_only=True)
class SerialCOM(BaseCOM):
    rx_address: str = field(default=None)

    @cached_property
    def prefix(self):
        return self.config["prefix"]

    @cached_property
    def suffix(self):
        return self.config["suffix"]

    async def connect(self, baudrate: int = 9600, timeout: int = 1) -> None:
        import serial
        import io

        async with self.lock:
            self.tx = serial.Serial(
                port=self.address, baudrate=baudrate, timeout=timeout
            )

            if self.rx_address is not None:
                # Add seperate response serial port, like for HiSeq 2500 FPGA
                self.rx = serial.Serial(
                    port=self.rx_address, baudrate=baudrate, timeout=timeout
                )
            else:
                # use the same serial port for responses, most instrumentation
                self.rx = self.tx

            self.com = io.TextIOWrapper(
                io.BufferedRWPair(self.tx, self.rx), encoding="ascii", errors="ignore"
            )

    async def write(self, command: str):
        command = f"{self.prefix}{command}{self.suffix}"
        self.com.write(command)
        self.com.flush()
        LOGGER.debug(f"{self.name} :: tx :: {command}")

    async def read(self) -> str:
        response = self.com.readline()
        LOGGER.debug(f"{self.name} :: rx :: {response}")
        return response

    async def command(self, command: str) -> str:
        async with self.lock:
            await self.write(command)
            return await self.read()

    async def close(self):
        async with self.lock:
            self.tx.close()
            if self.rx_address is not None:
                self.rx.close()


@define(kw_only=True)
class EmulatedSerialCOM(BaseCOM):
    config: dict

    @cached_property
    def prefix(self):
        return self.config["prefix"]

    @cached_property
    def suffix(self):
        return self.config["suffix"]

    async def connect(self) -> None:
        """Emulate connection to serial port"""
        async with self.lock:
            LOGGER.debug(f"{self.name} emulating connection to {self.address}")

    async def close(self) -> bool:
        """Emulate closing a connection to serial port.

        Returns:
            bool: True if the connection is gracefully closed, otherwise False.
        """
        async with self.lock:
            LOGGER.debug(f"{self.name} emulating closing connection to {self.address}")
        return True
