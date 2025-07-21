from __future__ import annotations
from abc import ABC, abstractmethod
from pyseq_core.utils import MACHINE_SETTINGS_PATH
from pyseq_core.base_com import BaseCOM
import yaml
from attrs import define, field
from typing import Union
from functools import cached_property
import time
import asyncio


@define
class BaseInstrument(ABC):
    name: str
    com: BaseCOM = field(init=False)
    config: dict = field(init=False)
    """
    Abstract base class for instrument implementations.

    This class defines the interface that all instrument classes must implement.
    Subclasses should provide concrete implementations for all abstract methods.

    Attributes:
        name (str): The name of the instrument.
        com (BaseCOM): The communication interface for the instrument.
        config (dict): The configuration settings for the instrument, loaded from a YAML file.
    """

    @config.default
    def get_config(self) -> dict:
        """Get instrument configuration settings from the machine settings file.

        This method reads the global machine settings file (MACHINE_SETTINGS_PATH),
        identifies the current machine's name, and then extracts the configuration
        specific to this instrument instance.

        Returns:
            dict: A dictionary containing the instrument's configuration settings.
                Returns an empty dictionary if the machine name or instrument
                configuration is not found.
        """
        # Get instrument configuration settings
        with open(MACHINE_SETTINGS_PATH, "r") as f:
            config = yaml.safe_load(f)  # Machine config
        machine_name = config.get("name", None)  # Machine name
        return config.get(machine_name, {}).get(self.name, {})

    async def command(self, command: Union[str, dict]):
        """Send a command string to the instrument.

        This method forwards the given command to the instrument's communication
        interface (`self.com`).

        Args:
            command (str, dict): The command string to send to the instrument.

        Returns:
            str,dict: The response received from the instrument's communication interface.
        """
        return await self.com.command(command)

    @abstractmethod
    async def initialize(self):
        """
        Initialize the instrument.

        This method should be implemented by subclasses to perform any setup
        required before the instrument can be used, such as configuring hardware.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """

    @abstractmethod
    async def shutdown(self):
        """Shutdown the instrument.

        This method should be implemented by subclasses to gracefully
        shutdown the instrument, releasing resources, or putting the hardware
        into a safe state.
        """

    @abstractmethod
    async def status(self) -> bool:
        """Retrieve the current operational status of the instrument.

        This method should be implemented by subclasses to query the instrument
        and determine its current state.

        Returns:
            bool: True if the instrument is operational and ready for use,
                False otherwise.
        """

    @abstractmethod
    async def configure(self):
        """Configure the instrument.

        This method should be implemented by subclasses to apply specific
        configuration settings to the instrument, typically based on the
        `self.config` attribute. This might involve sending commands to the
        hardware to set parameters or modes of operation.
        """


@define
class BaseStage(BaseInstrument):
    _position: Union[int, float] = field(init=False)
    """
    Abstract base class for a microscope stage instrument.

    This class extends `BaseInstrument` to define common properties and
    abstract methods for controlling a stage, such as moving to a position
    and retrieving the current position.

    Attributes:
        _position (Union[int, float]): The cached current position of the stage.
            This attribute is not initialized directly but is set by the `position` setter.
    """

    @cached_property
    def min_position(self) -> Union[float, int]:
        """The minimum allowed position for the stage.

        This value is retrieved from the instrument's configuration settings
        under the key "min_val".

        Returns:
            Union[float, int]: The minimum position.
        """
        return self.config.get("min_val")

    @cached_property
    def max_position(self) -> Union[float, int]:
        """The maximum allowed position for the stage.

        This value is retrieved from the instrument's configuration settings
        under the key "max_val".

        Returns:
            Union[float, int]: The maximum position.
        """
        return self.config.get("max_val")

    @abstractmethod
    async def move(self, positiion):
        """Move the stage to a specified position.

        This method should be implemented by subclasses to send commands to the
        physical stage to move it to the target position.

        Args:
            positiion (Union[int, float]): The target position to move the stage to.
        """

    @abstractmethod
    async def get_position(self):
        """Retrieve the current actual position of the stage.

        This method should be implemented by subclasses to query the physical
        stage for its current position and save it with the `position` setter.

        Returns:
            Union[int, float]: The current position of the stage.
        """
        pass

    @property
    def position(self):
        """Cached stage position.

        This property provides access to the internally stored position of the stage.
        It does not query the physical hardware.

        Returns:
            Union[int, float]: The cached current position of the stage.
        """
        return self._position

    @position.setter
    def position(self, position):
        """Set the current cached position of the stage.

        This setter updates the internal `_position` attribute. It does not
        move the physical stage; for that, use the `move` method.

        Args:
            position (Union[int, float]): The new position value to cache.
        """
        self._position = position


@define
class BasePump(BaseInstrument):
    """
    Abstract base class for a pump instrument.

    This class extends `BaseInstrument` to define common properties and
    abstract methods for controlling a pump, such as dispensing liquid
    at a specified volume and flow rate.
    """

    @cached_property
    def min_volume(self) -> Union[float, int]:
        """The minimum allowed volume for the pump.

        This value is retrieved from the instrument's configuration settings
        under the "volume" section and "min_val" key.

        Returns:
            Union[float, int]: The minimum volume.
        """
        return self.config.get("volume").get("min_val")

    @cached_property
    def max_volume(self) -> Union[float, int]:
        """The maximum allowed volume for the pump.

        This value is retrieved from the instrument's configuration settings
        under the "volume" section and "max_val" key.

        Returns:
            Union[float, int]: The maximum volume.
        """
        return self.config.get("volume").get("max_val")

    @cached_property
    def min_flow_rate(self) -> Union[float, int]:
        """The minimum allowed flow rate for the pump.

        This value is retrieved from the instrument's configuration settings
        under the "flow_rate" section and "min_val" key.

        Returns:
            Union[float, int]: The minimum flow rate.
        """
        return self.config.get("flow_rate").get("min_val")

    @cached_property
    def max_flow_rate(self) -> Union[float, int]:
        """The maximum allowed flow rate for the pump.

        This value is retrieved from the instrument's configuration settings
        under the "flow_rate" section and "max_val" key.

        Returns:
            Union[float, int]: The maximum flow rate.
        """
        return self.config.get("flow_rate").get("max_val")

    @abstractmethod
    async def pump(
        self, volume: Union[float, int], flow_rate: Union[float, int], **kwargs
    ):
        """Pump a specified volume at a specified flow rate from inlet to outlet of flowcell.

        This method should be implemented by subclasses to control the physical
        pump to dispense a given volume of liquid at a particular flow rate.

        Args:
            volume (Union[float, int]): The volume of liquid to pump.
            flow_rate (Union[float, int]): The rate at which to pump the liquid.
            **kwargs: Additional keyword arguments that might be specific to
                      a particular pump implementation (e.g., pause_time, waste_flow_rate).
        Returns:
            bool: True if succesfully pumped volume, otherwise False.
        """

    @abstractmethod
    async def reverse_pump(
        self, volume: Union[float, int], flow_rate: Union[float, int], **kwargs
    ):
        """Pump a specified volume at a specified flow rate from outlet to inlet of flowcell.

        This method should be implemented by subclasses to control the physical
        pump to withdraw a given volume of liquid at a particular flow rate.

        Args:
            volume (Union[float, int]): The volume of liquid to reverse pump.
            flow_rate (Union[float, int]): The rate at which to reverse pump the liquid.
            **kwargs: Additional keyword arguments that might be specific to
                      a particular pump implementation.
        Returns:
            bool: True if succesfully pumped volume, otherwise False.
        """
        pass


@define
class BaseValve(BaseInstrument):
    _port: Union[str, int] = field(init=False)
    """
    Abstract base class for a valve instrument.

    This class extends `BaseInstrument` to define common properties and
    abstract methods for controlling a valve, such as selecting a port
    and reading the current port.

    Attributes:
        _port (Union[str, int]): The cached current port of the valve.
            This attribute is not initialized directly but is set by the `port` setter
            or `initial_port_value` default.
    """

    @abstractmethod
    async def select(self, port: Union[str, int], **kwargs) -> bool:
        """Select a specific port on the valve.

        This method should be implemented by subclasses to send commands to the
        physical valve to switch to the specified port.

        Args:
            port (Union[str, int]): The identifier of the port to select.
            **kwargs: Additional keyword arguments that might be specific to
                      a particular valve implementation (e.g., speed, timeout).
        Returns:
            bool: True if succesfull select port, otherwise False.
        """

    @abstractmethod
    async def current_port(self) -> Union[str, int]:
        """Read the current active port from the valve.

        This method should be implemented by subclasses to query the physical
        valve and retrieve its currently selected port.

        Returns:
            Union[str, int]: The identifier of the current active port.
        """
        pass

    @_port.default
    def initial_port_value(self):
        """Provides the initial default value for the `_port` attribute.

        This method sets the initial cached port to the first port listed
        in the `ports` cached property (which is derived from the instrument's
        configuration). Initialize the Valve to this port in concrete subclasses.

        Returns:
            Union[str, int]: The first valid port from the configuration.
        """
        return self.ports[0]

    @cached_property
    def ports(self):
        """A list of valid ports supported by the valve.

        This value is retrieved from the instrument's configuration settings
        under the "valid_list" key.

        Returns:
            list[Union[str, int]]: A list of valid port identifiers.
        """
        return self.config.get("valid_list", [])

    @property
    def port(self):
        """Get the current cached port of the valve.

        This property provides access to the internally stored port of the valve.
        It does not query the physical hardware.

        Returns:
            Union[str, int]: The cached current port of the valve.
        """
        return self._port

    @port.setter
    def port(self, port):
        """Set the current cached port of the valve.

        This setter updates the internal `_port` attribute. It does not
        select the physical port; for that, use the `select` method.

        Args:
            port (Union[str, int]): The new port value to cache.
        """
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
    async def move(self, open: bool):
        """Open the shutter."""
        pass

    @abstractmethod
    async def close(self):
        """Close the shutter."""
        pass

    @property
    def open(self):
        """Position of shutter"""
        self._open

    @open.setter
    def open(self, open):
        """Set position of shutter"""
        self._open = open


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
