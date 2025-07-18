from abc import ABC, abstractmethod
from pyseq_core.utils import MACHINE_SETTINGS_PATH
import yaml
from attrs import define, field
from typing import Union
from functools import cached_property
import time
import asyncio


@define
class BaseCOM(ABC):
    address: str = field()
    lock: asyncio.Lock = field(factory=asyncio.Lock)

    @abstractmethod
    async def command(self, command: str):
        async with self.lock:
            pass

    @abstractmethod
    def initialize():
        pass


@define
class BaseInstrument(ABC):
    name: str
    com: BaseCOM = field(init=False)
    config: dict = field(init=False)

    @config.default
    def get_config(self) -> dict:
        # Get instrument configurationt settings
        with open(MACHINE_SETTINGS_PATH, "r") as f:
            config = yaml.safe_load(f)  # Machine config
        machine_name = config.get("name", None)  # Machine name
        return config.get(machine_name, {}).get(self.name, {})

    def command(self, command: str):
        return self.com.command(command)

    @abstractmethod
    async def initialize(self):
        """Initialize the instrument."""
        pass

    @abstractmethod
    async def shutdown(self):
        """Shutdown the instrument."""
        pass

    @abstractmethod
    async def get_status(self):
        """Retrieve the current status of the instrument."""
        pass

    @abstractmethod
    async def configure(self):
        """Configure the instrument."""
        pass


@define
class BaseStage(BaseInstrument):
    _position: Union[int, float] = field(init=False)

    @cached_property
    def min_position(self) -> Union[float, int]:
        return self.config.get("min_val")

    @cached_property
    def max_position(self) -> Union[float, int]:
        return self.config.get("max_val")

    @abstractmethod
    async def move(self, positiion):
        pass

    @abstractmethod
    async def get_position(self):
        pass

    @property
    def position(self):
        """Cached stage position."""
        return self._position

    @position.setter
    def position(self, position):
        """Set the current position of the stage."""
        self._position = position


@define
class BasePump(BaseInstrument):
    _volume: Union[float, int] = field(init=False)
    _flow_rate: Union[float, int] = field(init=False)

    @cached_property
    def min_volume(self) -> Union[float, int]:
        return self.config.get("volume").get("min_val")

    @cached_property
    def max_volume(self) -> Union[float, int]:
        return self.config.get("volume").get("max_val")

    @cached_property
    def min_flow_rate(self) -> Union[float, int]:
        return self.config.get("flow_rate").get("min_val")

    @cached_property
    def max_flow_rate(self) -> Union[float, int]:
        return self.config.get("flow_rate").get("max_val")

    @abstractmethod
    async def pump(self, volume, flow_rate, **kwargs):
        """Pump a specified volume at a specified flow rate."""
        pass

    @abstractmethod
    async def reverse_pump(self, volume, flow_rate, *kwargs):
        """Pump a specified volume at a specified flow rate in reverse direction."""
        pass


@define
class BaseValve(BaseInstrument):
    _port: Union[str, int] = field(init=False)

    @abstractmethod
    async def select(self, port, **kwargs):
        """Select port on the valve."""
        pass

    @abstractmethod
    async def current_port(self):
        """Read current port from valve."""
        pass

    @_port.default
    def initial_port_value(self):
        return self.ports[0]

    @_port.validator
    def _validate_port(self, attribute, value):
        if value not in self.ports:
            raise ValueError(f"Port {value} not listed on {self.name}")

    @cached_property
    def ports(self):
        return self.config.get("valid_list", [])

    @property
    def port(self):
        """Get current port."""
        return self._port

    @port.setter
    def port(self, port):
        """Set current port."""
        self._port = port


@define
class BaseLaser(BaseInstrument):
    color: str = field()
    _power: Union[int, float] = field(init=False)

    @cached_property
    def min_power(self):
        return self.config.get("min_val", 0)

    @cached_property
    def max_power(self):
        return self.config.get("max_val", 100)

    @abstractmethod
    async def set_power(self, power):
        pass

    @abstractmethod
    def get_power(self):
        pass

    @property
    def power(self):
        return self._power


class BaseYStage(BaseStage):
    pass


class BaseXStage(BaseStage):
    pass


class BaseZStage(BaseStage):
    pass


class BaseObjectiveStage(BaseStage):
    pass


@define
class BaseFilterWheel(BaseInstrument):
    _filters: dict = field(init=False)
    _filter: Union[float, str] = field(init=False)

    def __attrs_post_init__(self):
        self._filters = self.config.get("valid_list")

    @abstractmethod
    async def set_filter(self, filter):
        """Select a filter on the wheel."""
        pass

    @property
    def filter(self):
        """Get the cached filter."""
        return self._filter


@define
class BaseShutter(BaseInstrument):
    _open: bool = field(init=False)

    @abstractmethod
    async def open(self):
        """Open the shutter."""
        pass

    @abstractmethod
    async def close(self):
        """Close the shutter."""
        pass


class BaseCamera(BaseInstrument):
    _exposure: float = field(init=False)

    @abstractmethod
    async def capture(self):
        """Capture an image."""
        pass

    @abstractmethod
    async def save_image(self, filepath):
        """Get the captured image."""
        pass

    @abstractmethod
    async def set_exposure(self, time):
        """Set the exposure time for the camera."""
        pass

    @abstractmethod
    async def get_exposure(self, time):
        """Set the exposure time for the camera."""
        pass

    @property
    def exposure(self):
        """Get cached exposure time"""
        self._exposure

    @cached_property
    def min_exposure(self):
        return self.config.get("min_val")

    @cached_property
    def max_exposure(self):
        return self.config.get("max_val")


@define
class BaseTemperatureController(BaseInstrument):
    _temperature: Union[float, int] = field(init=False)

    @cached_property
    def min_temperature(self):
        return self.config.get("min_val")

    @cached_property
    def max_temperature(self):
        return self.config.get("max_val")

    # Don't use property setter, can't use explicity with async
    # ie can't do `await temperature = t`
    @abstractmethod
    async def set_temperature(self, temperature):
        """Set the temperature of the device."""
        pass

    # Don't use property getter, can't use explicity with async
    # ie can't do `await temperature`
    @abstractmethod
    async def get_temperature(self):
        """Get the current temperature of the device."""
        pass

    async def wait_for_temperature(self, temperature, timeout=None, interval=5):
        """Wait for the system to reach a specified temperature."""
        start = time.time()
        while self.get_temperature != temperature:
            if timeout is not None and start + timeout > time.time():
                break
            await asyncio.sleep(interval)
