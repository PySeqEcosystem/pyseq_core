from pyseq_core.base_system import BaseFlowCell, BaseMicroscope, BaseSequencer, ROI
from pyseq_core.base_protocol import Optics

# from pyseq_core.baseROI import BaseROI, TestROI
from pyseq_core.base_instruments import (
    BaseCamera,
    BaseShutter,
    BaseFilterWheel,
    BaseLaser,
    BaseXStage,
    BaseYStage,
    BaseZStage,
    BaseObjectiveStage,
    BasePump,
    BaseValve,
    BaseTemperatureController,
)
from typing import Literal
from attrs import define, field
import logging
import asyncio


LOGGER = logging.getLogger("PySeq")


class TestCOM:
    """Just for testing purposes define: initialize, shutdown, get_status, and
    configure. Normally these are defined in the instrument classes, and only
    command is defined.

    Do not inherit BaseCOM, it causes a TypeError.
    """

    async def initialize(self):
        """Initialize the instrument."""
        LOGGER.info(f"Initializing {self.name}")

    async def shutdown(self):
        """Shutdown the instrument."""
        LOGGER.info(f"Shutting down {self.name}")

    async def get_status(self):
        """Retrieve the current status of the instrument."""
        pass

    async def configure(self):
        LOGGER.info(f"Configuring {self.name}")
        pass

    async def command(self, command: str):
        """Send a command to the instrument."""
        LOGGER.info(f"{self.name}: Tx: {command}")


class TestCamera(TestCOM, BaseCamera):
    def __init__(self, name: str):
        super().__init__(name=name)
        self._exposure = 1

    async def capture(self):
        """Capture an image."""
        LOGGER.debug(f"Capturing image with {self.name}")
        return True

    async def save_image(self, im_name: str):
        """Save an image"""
        LOGGER.debug(f"{self.name}: Saving image as {im_name}.tif")
        return True

    async def set_exposure(self, time):
        LOGGER.debug(f"{self.name}: Set exposure to {time}")
        self._exposure = time

    async def get_exposure(self):
        return self.exposure


class TestShutter(TestCOM, BaseShutter):
    def __init__(self, name="Shutter"):
        super().__init__(name)

    async def open(self):
        """Open the shutter."""
        LOGGER.debug(f"Opening shutter {self.name}")
        return True

    async def close(self):
        """Close the shutter."""
        LOGGER.debug(f"Closing shutter {self.name}")
        return True


class TestFilterWheel(TestCOM, BaseFilterWheel):
    def __init__(self, color: str):
        super().__init__(f"{color}FilterWheel")

    async def set_filter(self, filter):
        """Select a filter on the wheel."""
        LOGGER.debug(f"Selecting filter {filter} on {self.name}")
        self._filter = filter


class TestLaser(TestCOM, BaseLaser):
    def __init__(self, color: str):
        super().__init__(f"{color}Laser", color=color)
        self._power = 0

    async def set_power(self, power):
        """Set laser power."""
        LOGGER.debug(f"Setting {self.name} to {power}")
        self._power = power

    async def get_power(self, power):
        """Set laser power."""
        return self.power


class TestYStage(TestCOM, BaseYStage):
    def __init__(self, name="YStage"):
        super().__init__(name)
        self._position = 0

    async def move(self, position):
        LOGGER.debug(f"Moving {self.name} to {position}")
        self.position = position

    async def get_position(self):
        return self._position


class TestXStage(TestCOM, BaseXStage):
    def __init__(self, name="XStage"):
        super().__init__(name)
        self._position = 0

    async def move(self, position):
        LOGGER.debug(f"Moving {self.name} to {position}")
        self.position = position

    async def get_position(self):
        return self._position


class TestTiltStage(TestCOM, BaseZStage):
    def __init__(self, name="TiltStage"):
        super().__init__(name)
        self._position = 0

    async def move(self, position):
        LOGGER.debug(f"Moving {self.name} to {position}")
        self.position = position

    async def get_position(self):
        return self._position


class TestObjectiveStage(TestCOM, BaseObjectiveStage):
    def __init__(self, name="ZStage"):
        super().__init__(name)
        self._position = 0

    async def move(self, position):
        LOGGER.debug(f"Moving {self.name} to {position}")
        self.position = position

    async def get_position(self):
        return self._position


class TestPump(TestCOM, BasePump):
    def __init__(self, name: str):
        super().__init__(name)

    async def pump(self, volume, flow_rate, pause_time=0.1, waste_flow_rate=12000):
        """Pump a specified volume at a specified flow rate."""
        LOGGER.debug(f"{self.name}::Pump {volume} uL at {flow_rate} uL/min")
        LOGGER.debug(f"{self.name}::Pause for {pause_time} s")
        LOGGER.debug(f"{self.name}::Purge at {waste_flow_rate} ul/min")
        return True

    async def reverse_pump(
        self, volume, flow_rate, pause_time=0.1, waste_flow_rate=12000
    ):
        """Pump a specified volume at a specified flow rate."""
        LOGGER.debug(f"{self.name}::Reverse pump {volume} uL at {flow_rate} uL/min")
        LOGGER.debug(f"{self.name}::Pause for {pause_time} s")
        LOGGER.debug(f"{self.name}::Reverse purge at {waste_flow_rate} ul/min")
        return True


@define
class TestValve(TestCOM, BaseValve):
    async def select(self, port):
        """Pump a specified volume at a specified flow rate."""

        if port in self.ports:
            LOGGER.debug(f"{self.name}:: Selecting {port}")
            self.port = port
            return True
        else:
            LOGGER.warning(f"{self.name}:: Port {port} not found")
            return False

    async def current_port(self):
        """Read current port from valve."""
        if self._port is None:
            self._port = 1
        return self._port


class TestTemperatureController(TestCOM, BaseTemperatureController):
    def __init__(self, name: str):
        super().__init__(name)
        self._temperature = 25

    async def set_temperature(self, temperature):
        """Set the temperature."""
        LOGGER.debug(f"Setting {self.name} to {temperature}C")
        self._temperature = temperature

    async def get_temperature(self):
        """Get the current temperature."""
        return self._temperature


@define
class TestMicroscope(BaseMicroscope):
    instruments: dict = field(init=False)

    @instruments.default
    def set_instruments(self):
        instruments = {
            "Camera": {
                "Camera_558_687": TestCamera("Camera_558_687"),
                "Camera_610_740": TestCamera("Camera_610_740"),
            },
            "FilterWheel": {
                "red": TestFilterWheel("red"),
                "green": TestFilterWheel("green"),
            },
            "Laser": {"red": TestLaser("red"), "green": TestLaser("green")},
            "Shutter": TestShutter(),
            "XStage": TestXStage(),
            "YStage": TestYStage(),
            "TiltStage": TestTiltStage(),
            "ZStage": TestObjectiveStage(),
        }
        return instruments

    async def _initialize(self):
        """Initialize the microscope."""

        LOGGER.info(f"Initializing {self.name}")
        # Initialize all components
        _ = []
        for instrument in self.instruments.values():
            if isinstance(instrument, dict):
                # instruments organized in nested dict
                for nest_instrument in instrument.values():
                    _.append(nest_instrument._initialize())
            else:
                _.append(instrument._initialize())
        await asyncio._gather(*_)

    async def _shutdown(self):
        """Shutdown the microscope."""

        LOGGER.info(f"Shutting down {self.name}")
        # Shutdown all components
        _ = []
        for instrument in self.instruments.values():
            if isinstance(instrument, dict):
                # instruments organized in nested dict
                for nest_instrument in instrument.values():
                    _.append(nest_instrument._shutdown())
            else:
                _.append(instrument._shutdown())
        await asyncio._gather(*_)

    async def _configure(self):
        LOGGER.info(f"Configure down {self.name}")
        # Configure all components
        _ = []
        for instrument in self.instruments.values():
            if isinstance(instrument, dict):
                # instruments organized in nested dict
                for nest_instrument in instrument.values():
                    _.append(nest_instrument._configure())
            else:
                _.append(instrument._configure())
        await asyncio._gather(*_)

    async def _capture(self, roi: ROI, im_name: str):
        """Capture an image and save it to the specified filename."""

        LOGGER.debug(f"Acquire {im_name}")
        await self.Shutter.open()
        await self.YStage.move(roi.stage.y_last)
        await self.Shutter.close()
        _ = []
        for c in self.Camera.values():
            _.append(c.save_image(im_name))
        _.append(self.YStage.move(roi.stage.y_init))
        await asyncio.gather(*_)

    async def _z_stack(self, roi: ROI, im_name: str):
        """Perform a z-stack acquisition."""

        direction = roi.stage.z_direction
        step = roi.stage.z_step
        if direction == 1:
            z_init = roi.stage.z_init
            z_last = roi.stage.z_last
        else:
            z_init = roi.stage.z_last
            z_last = roi.stage.z_init
        LOGGER.debug(f"Z stack {roi.name} {z_init} to {z_last} in {step} steps")
        for i, z in enumerate(range(z_init, z_last, direction * step)):
            LOGGER.debug(f"Z stack {i}/{roi.stage.nz}")
            await self.ZStage.move(z)
            await self._capture(roi, f"{im_name}_z{z}")

    async def _scan(self, roi: ROI, im_name: str = ""):
        """Perform a scan over the specified region of interest (ROI)."""

        x_init = roi.stage.x_init
        x_last = roi.stage.x_last
        x_step = roi.stage.x_step * roi.stage.x_direction
        LOGGER.debug(
            f"Scanning {roi.name}: XStage: {x_init} to {x_last} in {x_step} increments"
        )
        if len(im_name) == 0:
            im_name = roi.name
        for i, x in enumerate(range(x_init, x_last, x_step)):
            LOGGER.debug(f"XStage {i}/{roi.stage.nx}")
            await self.XStage.move(x)
            await self._z_stack(roi, f"{im_name}_x{x}")

    async def _expose_scan(self, roi: ROI):
        """Async expose the sample for a specified duration without imaging."""

        x_init = roi.stage.x_init
        x_last = roi.stage.x_last
        x_step = roi.stage.x_step * roi.stage.x_direction
        n_exposures = roi.expose.n_exposures
        LOGGER.debug(
            f"Exposing {roi.name}: XStage: {x_init} to {x_last} in {x_step} increments"
        )
        for i, x in enumerate(range(x_init, x_last, x_step)):
            LOGGER.debug(f"XStage {i}/{roi.stage.nx}")
            await self.XStage.move(x)
            for n in range(n_exposures):
                LOGGER.debug(f"Exposure {n}/{n_exposures}")
                if self.YStage.position == roi.y_init:
                    await self.YStage.move(roi.y_last)
                else:
                    await self.YStage.move(roi.y_init)

    async def _find_focus(self, roi):
        LOGGER.debug(f"Fake finding focus using routine {roi.focus.routine}.")
        LOGGER.debug(f"Saving focus data to {roi.focus.output}.")
        roi.focus.z_focus = 0

    async def _move(self, roi: ROI):
        """Move the stage ROI x,y,z coordinates."""
        LOGGER.debug(f"Moving to x={roi.x}, y={roi.y}, z={roi.z}")
        await asyncio.gather(
            self.XStage.move(roi.x),
            self.YStage.move(roi.y),
            self.ZStage.move(roi.z),
        )

    async def _set_parameters(
        self, params: Optics, mode: Literal["image", "focus", "expose"]
    ):
        """Set the parameters to expose/image the ROI."""

        params = params.model_dump()[mode]["optics"]
        _ = []
        for color in ["red", "green"]:
            _.append(self.Laser[color].set_power(params["power"][color]))
            _.append(self.FilterWheel[color].set_filter(params["filter"][color]))

        if mode in ["image", "focus"]:
            for c in self.Camera:
                _.append(self.Camera[c].set_exposure(params["exposure"][c]))
        await asyncio.gather(*_)


@define(kw_only=True)
class TestFlowCell(BaseFlowCell):
    name: str = "FlowCell"
    instruments: dict = field(init=False)

    @instruments.default
    def set_instruments(self):
        instruments = {
            "Pump": TestPump(name=f"Pump{self.name}"),
            "Valve": TestValve(name=f"Valve{self.name}"),
            "TemperatureController": TestTemperatureController(
                name=f"TemperatureController{self.name}"
            ),
        }
        return instruments

    async def _initialize(self):
        """Initialize the flowcell."""

        LOGGER.info(f"Initializing {self.name}")
        # Initialize all components
        _ = []
        for instrument in self.instruments.values():
            _.append(instrument.initialize())
        await asyncio._gather(*_)

    async def _shutdown(self):
        """Shutdown the flowcell."""

        LOGGER.info(f"Shutting down {self.name}")

        # Shutdown all components
        _ = []
        for instrument in self.instruments.values():
            _.append(instrument._shutdown())
        await asyncio._gather(*_)

    async def _configure(self):
        """Configure the flowcell."""

        LOGGER.info(f"Configure {self.name}")

        # Shutdown all components
        _ = []
        for instrument in self.instruments.values():
            _.append(instrument._configure())
        await asyncio._gather(*_)


@define
class TestSequencer(BaseSequencer):
    """
    A test sequencer that does not perform any actual sequencing.
    It is used for testing purposes only.
    """

    _flowcells: dict = field(init=False)
    _microscope: TestMicroscope = field(factory=TestMicroscope)
    _enable: dict = {fc: True for fc in ["A", "B"]}

    @_flowcells.default
    def set_flowcells(self):
        return {fc: TestFlowCell(name=fc) for fc in ["A", "B"]}

    async def _initialize(self):
        LOGGER.info(f"Initializing {self.name}")
        _ = []
        for fc in self._flowcells:
            _.append(self._flowcells[fc]._initialize())
        _.append(self.microscope._initialize())
        await asyncio.gather(*_)

    async def _shutdown(self):
        LOGGER.info(f"Shutting down {self.name}")
        _ = []
        for fc in self._flowcells:
            _.append(self._flowcells[fc]._shutdown())
        _.append(self.microscope._shutdown())
        await asyncio.gather(*_)

    async def _configure(self):
        LOGGER.info(f"Configuring {self.name}")
        _ = []
        for fc in self._flowcells:
            _.append(self._flowcells[fc]._configure())
        _.append(self.microscope._configure())
        await asyncio.gather(*_)

    def custom_roi_factory(self, name: str, **kwargs) -> ROI:
        """Take LLx, LLy, URx, URy coordinates and return an ROI with stage coordinates."""
        LLx = kwargs.pop("LLx") * 100
        LLy = kwargs.pop("LLy") * 100
        URx = kwargs.pop("URx") * 100
        URy = kwargs.pop("URy") * 100
        fc = kwargs.get("flowcell")

        # x, y, Steps Per UMicron
        x_spum = self.microscope.XStage.config["spum"]
        y_spum = self.microscope.YStage.config["spum"]
        # x, y origin
        x_origin = self.microscope.XStage.config["origin"][fc]
        y_origin = self.microscope.YStage.config["origin"]

        x_init = LLx * x_spum + x_origin
        x_last = URx * x_spum + x_origin
        y_init = URy * y_spum + y_origin
        y_last = LLy * y_spum + y_origin

        stage = {
            "flowcell": fc,
            "x_init": x_init,
            "x_last": x_last,
            "y_init": y_init,
            "y_last": y_last,
        }
        stage.update(kwargs.pop("stage", {}))

        return ROI(name=name, stage=stage, **kwargs)
