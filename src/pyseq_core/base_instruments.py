from abc import ABC, abstractmethod
from pyseq_core.utils import MACHINE_SETTINGS_PATH
import yaml
from attrs import define, field
from typing import Union
from functools import cached_property
from warnings import warn


@define
class BaseCOM:
    @abstractmethod
    async def command(self, command: str):
        pass


@define
class BaseInstrument(ABC):
    name: str
    com: BaseCOM = field(init=False)
    config: dict = field(init=False)

    # def _init__(self, name):
    #     self.name = name
    #     self.load_configuration()

    @config.default
    def get_config(self):
        # def __attrs_pre_init__(self):
        # def __attrs_post_init__(self):
        # Get instrument configurationt settings
        with open(MACHINE_SETTINGS_PATH, "r") as f:
            config = yaml.safe_load(f)  # Machine config
        machine_name = config.get("name", None)  # Machine name
        return config.get(machine_name, {}).get(self.name, {})

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

    # Base COM define how instruments communicate
    # @abstractmethod
    # async def command(self, command):
    #     """Send a command to the instrument."""
    #     pass

    @abstractmethod
    async def configure(self):
        """Configure the instrument."""
        pass

    # @config.default
    # def get_config(self):
    #     with open (MACHINE_SETTINGS_PATH, 'r') as f:
    #         config = yaml.safe_load(f) # Machine config
    #         machine_name = config.get('name') # Machine name
    #         return config.get(machine_name, {}).get(self.name, {})


@define
class BaseStage(BaseInstrument):
    _position: Union[int, float] = field(init=False)
    _min_position: Union[int, float] = field(init=False)
    _max_position: Union[int, float] = field(init=False)
    # _position = param.Number(bounds = (BaseInstrument.config.get('min_position', 0),
    #                                    BaseInstrument.config.get('max_position', 100)),
    #                          instantiate = True,)

    def __attrs_post_init__(self):
        self._min_position = self.config.get("min position", 0)
        self._max_position = self.config.get("max position", 100)

    def __call__(self, position):
        self._position = position

    @_position.validator
    def _validate_position(self, attribute, value):
        min_val = self.min_position
        max_val = self.max_position

        if not min_val <= value <= max_val:
            raise ValueError(
                f"{self.name} position must be between {min_val} and {max_val}"
            )

    @property
    def min_position(self):
        return self._min_position

    @property
    def max_position(self):
        return self._max_position

    @property
    @abstractmethod
    async def position(self, position):
        """Move the stage to a specified position."""
        pass

    @position.getter
    @abstractmethod
    async def position(self):
        """Get the current position of the stage."""
        pass


@define
class BasePump(BaseInstrument):
    _volume: Union[float, int] = field(init=False)
    _flow_rate: Union[float, int] = field(init=False)

    # _volume = param.Number(bounds = (BaseInstrument.config.get('min_volume', 0),
    #                                  BaseInstrument.config.get('max_volume', 100)),
    #                        instantiate = True,)
    # _flow_rate = param.Number(bounds = (BaseInstrument.config.get('min_flow_rate', 0),
    #                                     BaseInstrument.config.get('max_flow_rate', 100)),
    #                           instantiate = True,)

    @_volume.validator
    def _validate_volume(self, attribute, value):
        min_val = self.min_volume
        max_val = self.max_volume

        if not min_val <= value <= max_val:
            raise ValueError(f"Volume must be between {min_val} and {max_val}")

    @_flow_rate.validator
    def _validate_flow_rate(self, attribute, value):
        min_val = self.min_flow_rate
        max_val = self.max_flow_rate

        if not min_val <= value <= max_val:
            raise ValueError(f"Flow rate must be between {min_val} and {max_val}")

    def __call__(self, volume=None, flow_rate=None) -> bool:
        """Validate pump volume and flow rate."""
        try:
            if volume is not None:
                self._volume = volume
            if flow_rate is not None:
                self._flow_rate = flow_rate
            return True
        except ValueError as e:
            warn(f"{e}", UserWarning)
            return False

    @property
    @abstractmethod
    def min_volume(self):
        pass

    @property
    @abstractmethod
    def max_volume(self):
        pass

    @property
    @abstractmethod
    def min_flow_rate(self):
        pass

    @property
    @abstractmethod
    def max_flow_rate(self):
        pass

    @abstractmethod
    async def pump(self, volume, flow_rate, pause):
        """Pump a specified volume at a specified flow rate."""
        pass

    @abstractmethod
    async def reverse_pump(self, volume, flow_rate, pause):
        """Pump a specified volume at a specified flow rate in reverse direction."""
        pass


@define
class BaseValve(BaseInstrument):
    # _n_ports: int = field(init=False)
    # ports: list = field(init=False)
    # _blocked_ports = field(init=False)
    _port: Union[str, int] = field(init=False)

    # async def __attrs_post_init__(self):
    # await self.current_port()
    # self._n_ports = self.config.get('n_ports', 2)
    # self._blocked_ports = self.config.get('blocked ports', [])
    # if len(self.ports) == 0:
    #     ports = {}
    #     for p in range(self._n_ports):
    #         if p+1 not in self._blocked_ports:
    #             ports[p+1] = p+1
    #     self.ports = ports

    def __call__(self, port) -> bool:
        """Validate port selection on the valve."""
        try:
            [_port, self._port] = [
                self._port,
                port,
            ]  # Save current port and validate new port
            return True
        except ValueError as e:
            warn(f"{e}", UserWarning)
            return False
        finally:
            self._port = _port  # Put current port back in place

    @abstractmethod
    async def select(self, port):
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
        if value in self._blocked_ports:
            raise ValueError(f"Port {value} blocked on {self.name}")
        if value not in self.ports:
            raise ValueError(f"Port {value} not listed on {self.name}")

    @cached_property
    def _n_ports(self):
        return self.config.get("n_ports", 2)

    @cached_property
    def _blocked_ports(self):
        return self.config.get("blocked ports", [])

    @cached_property
    def ports(self):
        ports = []
        for p in range(self._n_ports):
            if p + 1 not in self._blocked_ports:
                ports.append(p + 1)
        return ports

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
    color: str = field(init=False)
    _power: Union[int, float] = field(init=False)
    _min_power: Union[int, float] = field(init=False)
    _max_power: Union[int, float] = field(init=False)
    # _power = param.Number(bounds = (BaseInstrument.config.get('min_power', 0),
    #                                 BaseInstrument.config.get('max_power', 100)),
    #   instantiate = True,)

    def __call__(self, power):
        self._power = power

    @_power.validator
    def _validate_power(self, attribute, value):
        min_val = self.min_power
        max_val = self.max_power

        if not min_val <= value <= max_val:
            raise ValueError(
                f"{self.name} power must be between {min_val} and {max_val}"
            )

    @cached_property
    def min_power(self):
        return self.config.get("min power", 0)

    @cached_property
    def max_power(self):
        return self.config.get("max power", 100)

    @property
    @abstractmethod
    async def power(self):
        """Abstract property for setting laser power."""
        pass

    @power.getter
    @abstractmethod
    async def power(self):
        """Get the current laser power."""
        pass


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
    filters: dict = field(init=False)
    _filter: Union[float, str] = field(init=False)
    # _filter_dict = BaseInstrument.config.get('filters', {'home':0, 'open':1})
    # _filter = param.Selector(objects = [str(k) for k in _filter_dict.keys()],
    #                          instantiate = True,)

    def __call__(self, filter):
        self._filter = filter

    @_filter.validator
    def validate_filter(self, attribute, value):
        if value not in self.filters:
            raise ValueError(f"Filter {value} not listed on {self.name}")

    @property
    @abstractmethod
    async def filter(self, filter):
        """Select a filter on the wheel."""
        pass

    @filter.getter
    @abstractmethod
    async def filter(self):
        """Get the currently selected filter."""
        pass


@define
class BaseShutter(BaseInstrument):
    _open: bool = field(init=False)

    # async def __call__(self):
    #     if self._open:
    #         await self.close()
    #     else:
    #         await self.open()

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

    def __call__(self, exposure: float):
        self._exposure = exposure

    @_exposure.validator
    def validate_exposure(self, attribute, value):
        min_val = self.min_exposure
        max_val = self.max_exposure

        if not min_val <= value <= max_val:
            raise ValueError(
                f"{self.name} exposure must be between {min_val} and {max_val}"
            )

    @property
    @abstractmethod
    async def exposure(self, time):
        """Set the exposure time for the camera."""
        pass

    @exposure.setter
    @abstractmethod
    async def exposure(self):
        """Get the current exposure time of the camera."""
        pass

    @cached_property
    def min_exposure(self):
        return self.config.get("min exposure", 0.0)

    @cached_property
    def max_exposure(self):
        return self.config.get("max exposure", 10.0)


@define
class BaseTemperatureController(BaseInstrument):
    _temperature: Union[float, int] = field(init=False)
    # _temperature = param.Number(bounds = (BaseInstrument.config.get('min_temperature', 4),
    #                                       BaseInstrument.config.get('max_temperature', 50)),
    #                             instantiate = True,)

    def __call__(self, temperature):
        self._temperature = temperature

    @_temperature.validator
    def validate_temperaute(self, attribute, value):
        min_val = self.min_temperature
        max_val = self.max_temperature

        if not min_val <= value <= max_val:
            raise ValueError(
                f"{self.name} temperature must be between {min_val} and {max_val}"
            )

    @property
    @abstractmethod
    def min_temperature(self):
        pass

    @property
    @abstractmethod
    def max_temperature(self):
        pass

    @property
    @abstractmethod
    async def temperature(self, temperature):
        """Set the temperature of the device."""
        pass

    @temperature.setter
    @abstractmethod
    async def temperature(self):
        """Get the current temperature of the device."""
        pass

    @abstractmethod
    async def wait_for_temperature(self, temperature, timeout=None):
        """Wait for the system to reach a specified temperature."""
        pass
