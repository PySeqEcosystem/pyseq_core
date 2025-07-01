from pyseq_core.base_system import BaseFlowCell, BaseMicroscope, BaseSequencer, ROI
# from pyseq_core.baseROI import BaseROI, TestROI
from pyseq_core.base_instruments import (
    BaseCamera, BaseShutter, BaseFilterWheel, BaseLaser,
    BaseXStage, BaseYStage, BaseZStage, BaseObjectiveStage,  
    BasePump, BaseValve, BaseTemperatureController,
)
from typing import Literal
from attrs import define, field, asdict
import logging
import asyncio



LOGGER = logging.getLogger('PySeq')
# LOG_CONFIG_PATH = Path.home() / '.config/pyseq2500/logger_config.yaml'

# with open(LOG_CONFIG_PATH, 'r') as f:
#     log_config = yaml.safe_load(LOG_CONFIG_PATH)
# LOGGER.config.dictConfig(log_config)



class TestCOM():
    """Just for testing purposes define: initialize, shutdown, get_status, and 
       configure. Normally these are defined in the instrument classes, and only
       command is defined.

       Do not inherit BaseCOM, it causes a TypeError.
    """

    async def initialize(self):
        """Initialize the instrument."""
        LOGGER.info(f"Initializing {self._name}")  

    async def shutdown(self):
        """Shutdown the instrument."""
        LOGGER.info(f"Shutting down {self._name}")

    async def get_status(self):
        """Retrieve the current status of the instrument."""
        pass

    async def configure(self):
        LOGGER.info(f"Configuring {self._name}")
        pass

    async def command(self, command:str):
        """Send a command to the instrument."""
        LOGGER.info(f"{self._name}: Tx: {command}")


class TestCamera(TestCOM, BaseCamera):
    def __init__(self, name:str):
        super().__init__(name=name)
        self._name = name
        self._exposure = 1

    async def capture(self):
        """Capture an image."""
        LOGGER.debug(f"Capturing image with {self._name}")
        return True
    
    async def save_image(self):
        """Save an image"""
        LOGGER.debug(f"Saving image from {self._name}")
        return True
    
    @property
    async def exposure(self, time): 
        self._exposure = time

    @exposure.getter
    async def exposure(self):   
        return self._exposure
    
class TestShutter(TestCOM, BaseShutter):
    def __init__(self, name="Shutter"):
        super().__init__(name)

    async def open(self):
        """Open the shutter."""
        LOGGER.debug(f"Opening shutter {self._name}")
        return True

    async def close(self):
        """Close the shutter."""
        LOGGER.debug(f"Closing shutter {self._name}")
        return True

class TestFilterWheel(TestCOM, BaseFilterWheel):
    def __init__(self, color:str):
        super().__init__(f"{color}Filter")

    @property
    async def filter(self, filter):
        """Select a filter on the wheel."""
        LOGGER.debug(f"Selecting filter {filter} on {self._name}")
        self._filter = filter


    @filter.getter
    async def filter(self):
        """Get the currently selected filter."""
        return self._filter

class TestLaser(TestCOM, BaseLaser):
    def __init__(self, color:str):
        super().__init__(f"{color}Filter")
        self._power = 0

    @property
    async def power(self, power):
        """Set laser power."""
        LOGGER.debug(f"Setting {self._name} laser to {self._power}")
        self._power = power
    
    @power.getter
    async def power(self):
        """Get laser power."""
        return self._power
    
    @property
    def min_power(self):
        return 0

    @property
    def max_power(self):
        return 500
    
class TestYStage(TestCOM, BaseYStage):
    def __init__(self, name="YStage"):
        super().__init__(name)
        self._position = 0

    @property
    async def position(self, position):
        """Move the stage to a new position."""
        LOGGER.debug(f"Moving {self._name} to {position}")
        self._position = position

    @position.getter
    async def position(self):
        """Get the current position of the stage."""
        return self._position

class TestXStage(TestCOM, BaseXStage):
    def __init__(self, name="XStage"):
        super().__init__(name)
        self._position = 0

    @property
    async def position(self, position):
        """Move the stage to a new position."""
        LOGGER.debug(f"Moving {self._name} to {position}")
        self._position = position

    @position.getter
    async def position(self):
        """Get the current position of the stage."""
        return self._position

class TestZStage(TestCOM, BaseZStage):
    def __init__(self, name="ZStage"):
        super().__init__(name)
        self._position = 0

    @property
    async def position(self, position):
        """Move the stage to a new position."""
        LOGGER.debug(f"Moving {self._name} to {position}")
        self._position = position

    @position.getter
    async def position(self):
        """Get the current position of the stage."""
        return self._position

class TestObjectiveStage(TestCOM, BaseObjectiveStage):
    def __init__(self, name="ObjStage"):
        super().__init__(name)
        self._position = 0

    @property
    async def position(self, position):
        """Move the stage to a new position."""
        LOGGER.debug(f"Moving {self._name} to {position}")
        self._position = position

    @position.getter
    async def position(self):
        """Get the current position of the stage."""
        return self._position


class TestPump(TestCOM, BasePump):
    def __init__(self, name:str):
        super().__init__(name)

    async def pump(self, volume, flow_rate, pause=0.1):
        """Pump a specified volume at a specified flow rate."""
        LOGGER.debug(f"{self.name}::Pump {volume} uL at {flow_rate} uL/min")
        print(f"{self.name}::simulated sleep for {volume/flow_rate} s")
        # await asyncio.sleep(volume/flow_rate)
        print(f"{self.name}::Pumped {volume} uL at {flow_rate} uL/min")
        return True
    
    async def reverse_pump(self, volume, flow_rate, pause=0.1):
        """Pump a specified volume at a specified flow rate."""
        LOGGER.debug(f"{self.name}::Reverse pump {volume} uL at {flow_rate} uL/min")
        return True
    
    @property
    def min_volume(self):
        return 0
    
    @property
    def max_volume(self):
        return 2000
    
    @property
    def min_flow_rate(self):
        return 100
    
    @property
    def max_flow_rate(self):
        return 20000

@define    
class TestValve(TestCOM, BaseValve):
    # def __init__(self, name:str, ports:dict={}):
    #     BaseValve.__init__(self, name)
        # if len(ports) == 0:
        #     ports = {i:i for i in range(1, self._n_ports+1)}
        # self._ports = ports

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
    def __init__(self, name:str):
        super().__init__(name)
        self._temperature = 25

    @property
    async def temperature(self, temperature):
        """Set the temperature."""
        LOGGER.debug(f"Setting {self._name} to {temperature}C")
        self._temperature = temperature

    @temperature.getter
    async def temperature(self):
        """Get the current temperature."""
        return self._temperature
    

    async def wait_for_temperature(self, temperature):
        """Wait for the flowcell  to reach a specified temperature."""
        return await self.temperature(temperature)

    @property
    def min_temperature(self):
        return 4

    @property
    def max_temperature(self):
        return 60

@define
class TestMicroscope(BaseMicroscope):
    instruments: dict = field(init=False)
    # def __init__(self):
    #     super().__init__(name='TestMicroscope')
    #     self.instruments = {'Camera': {'red':TestCamera('red'), 'green':TestCamera('green')},
    #                         'FilterWheek': {'red':TestFilterWheel('red'), 'green':TestFilterWheel('green')},
    #                         'Laser': {'red':TestLaser('red'), 'green':TestLaser('green')},
    #                         'Shutter': TestShutter(),
    #                         'XStage': TestXStage(),
    #                         'YStage': TestYStage(),
    #                         'ZStage': TestZStage(),
    #                         'ObjStage': TestObjectiveStage(),
    #     }

    @instruments.default
    def set_instruments(self):
        instruments = {'Camera': {'red':TestCamera('red'), 'green':TestCamera('green')},
                        'FilterWheek': {'red':TestFilterWheel('red'), 'green':TestFilterWheel('green')},
                        'Laser': {'red':TestLaser('red'), 'green':TestLaser('green')},
                        'Shutter': TestShutter(),
                        'XStage': TestXStage(),
                        'YStage': TestYStage(),
                        'ZStage': TestZStage(),
                        'ObjStage': TestObjectiveStage(),
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

    async def _capture(self, roi:ROI, im_name:str):
        """Capture an image and save it to the specified filename."""
        xpos = self.XStage._position
        zpos = self.ObjStage._position
        im_name = f"{im_name}_x{xpos}_z{zpos}"
        LOGGER.debug(f"Acquire {im_name}")
        await self.Shutter.open()
        await self.YStage.position(roi.y_last)
        await self.Shutter.close()
        LOGGER.debug(f"Image saved to {im_name}.tif")
        await self.YStage.position(roi.y_init)

    async def _z_stack(self, roi:ROI, im_name:str, direction:Literal[1,-1]=1):
        """Perform a z-stack acquisition."""
        LOGGER.debug(f"Z stack {roi.name} {roi.z_init} to {roi.z_last} in {roi.z_step} steps")
        if direction == 1:
            z_init = roi.z_init
            z_last = roi.z_last
        else:
            z_init = roi.z_last
            z_last = roi.z_init
        for i, z in enumerate(range(z_init, z_last, direction*roi.z_step)):
            LOGGER.debug(f"Z stack {i}/{roi.nz}")
            await self._ZStage.position(z)
            await self._capture(roi, im_name)

        
    async def _scan(self, roi:ROI, im_name:str):
        """Perform a scan over the specified region of interest (ROI)."""
        LOGGER.debug(f"Scanning {roi.name} {roi.x_init} to {roi.x_last} in {roi.x_step} steps")
        if im_name is None:
            im_name = roi.name
        for i, x in enumerate(range(roi.x_init, roi.x_last, roi.x_step)):
            await self._XStage.position(x)
            await self._z_stack(roi)

    async def _expose_scan(self, roi:ROI, duration:int):
        """Async expose the sample for a specified duration without imaging."""
        
        for i, x in enumerate(range(roi.x_init, roi.x_last, roi.x_step)):
            LOGGER.debug(f"Exposing {roi.name} {i}/{roi.nx} at xstep={x}")
            await self._XStage.position(x)
            roi.x = x
            for n in range(duration):
                if roi.y == roi.y_init:
                    await self._YStage.position(roi.y_last)
                    roi.y = roi.y_last
                else:
                    await self._YStage.position(roi.y_init)
                    roi.y = roi.y_init

    async def _find_focus(self, roi):
        pass

    async def _move(self, roi:ROI):
        """Move the stage ROI x,y,z coordinates."""
        LOGGER.debug(f"Moving {roi.name} to x={roi.x}, y={roi.y}, z={roi.z}")
        asyncio.gather(self._XStage.position(roi.x), 
                       self._YStage.position(roi.y), 
                       self._ZStage.position(roi.z))

    async def _set_parameters(self, roi_params:ROI, mode:Literal['image','focus','expose']):
        """Set the parameters to expose/image the ROI."""

        params = asdict(roi_params)[mode]
        _ = []
        for color in ['red', 'green']:
            if mode in ['image','focus']:
                _.append(self._Camera[color].exposure(params['exposure'][color]))
            _.append(self._Laser[color].power(params['laser_power'][color]))
            _.append(self._FilterWheel[color].filter(params['filter'][color]))
        await asyncio.gather(*_)


@define(kw_only=True)
class TestFlowCell(BaseFlowCell):
    name: str = 'FlowCell'
    instruments: dict = field(init=False)

    @instruments.default
    def set_instruments(self):
        instruments = {'Pump': TestPump(name=f'Pump{self.name}'),
                       'Valve': TestValve(name=f'Valve{self.name}'),
                       'TemperatureController': TestTemperatureController(name=f'TemperatureController{self.name}')}
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


    async def _select_port(self, port):
        await self.Valve.select(port)
        print(f"{self.name} :: Selected {port}")

    async def _pump(self, volume, flow_rate, **kwargs):
        """Pump a specified volume of a reagent at a specified flow rate."""
        # if port is not None:
        #     self.select_port(port) #Add task so port change is added to logs
        print(f"{self.name} :: Pumping {volume} at {flow_rate}")
        await self.Pump.pump(volume, flow_rate)
        print(f"{self.name} :: Pumped {volume} at {flow_rate}")

    async def _reverse_pump(self, volume, flow_rate, **kwargs):
        """Pump a specified volume of a reagent at a specified flow rate."""
        # if port is not None:
        #     self.select_port(port) #Add task so port change is added to logs
        await self.Pump.reverse_pump(volume, flow_rate)

    async def _temperature(self, temperature):
        """Set the temperature of the flow cell."""
        await self._TemperatureController.temperature(temperature)

    # async def _hold(self, duration: numbers.Real):
    #     """Async hold for specified duration seconds."""
    #     await asyncio.sleep(duration)


    # async def _wait(self, event):
    #     """Async wait for an event"""
    #     if len(self.FlowCellSignal._listeners) == 0:
    #         pass
    #     else:
    #         self.FlowCellSignal.events.update({event: asyncio.Event()})
    #     await self.FlowCellSignal.events[event].wait()
    #     try:
    #         del self.FlowCellSignal.events[event]
    #     except KeyError:
    #         LOGGER.warning(f"Event {event} not found in FlowCellSignal events")


    # async def _user_wait(self, message, timeout=None):
    #     """Async end message to the user and wait for a response."""
    #     async with asyncio.timeout(timeout):
    #         await asyncio.to_thread(input, message)


        

@define
class TestSequencer(BaseSequencer):
    """
    A test sequencer that does not perform any actual sequencing.
    It is used for testing purposes only.
    """
    _flowcells: dict = field(init=False)
    _microscope: TestMicroscope = field(factory=TestMicroscope)
    _enable: dict = {fc: True for fc in ['A', 'B']}


    @_flowcells.default
    def set_flowcells(self):
        return {fc: TestFlowCell(name=fc) for fc in ['A','B']}

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
        LLx = kwargs.pop('LLx')
        LLy = kwargs.pop('LLy')
        URx = kwargs.pop('URx')
        URy = kwargs.pop('URy')
        fc = kwargs.get('flowcell')

        #x, y, Steps Per UMicron
        x_spum = self.microscope.XStage.config['spum']
        y_spum = self.microscope.YStage.config['spum']
        # x, y origin
        x_origin = self.microscope.XStage.config['origin'][fc]
        y_origin = self.microscope.YStage.config['origin']

        x_init = LLx*x_spum + x_origin
        x_last = URx*x_spum + x_origin
        y_init = URy*y_spum + y_origin
        y_last = LLy*y_spum + y_origin

        stage = {'flowcell': fc, 
                 'x_init': x_init, 'x_last': x_last, 
                 'y_init': y_init, 'y_last': y_last}
        stage.update(kwargs.pop('stage', {}))

        return ROI(name=name, stage=stage, **kwargs)


