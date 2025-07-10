from abc import ABC, abstractmethod
from pyseq_core.utils import DEFAULT_CONFIG, HW_CONFIG
from pyseq_core.base_instruments import (
    BaseYStage,
    BaseXStage,
    BaseZStage,
    BaseObjectiveStage,
    BaseShutter,
    BaseFilterWheel,
    BaseLaser,
    BaseCamera,
    BasePump,
    BaseValve,
    BaseTemperatureController,
)
from pyseq_core.base_reagents import ReagentsManager
from pyseq_core.base_protocol import (
    Optics,
    HoldCommand,
    WaitCommand,
    TemperatureCommand,
)
from pyseq_core.base_protocol import (
    BaseROIFactory,
    SimpleStageFactory,
    PumpCommandFactory,
)
from pyseq_core.base_protocol import (
    read_protocol,
    format_protocol,
    need_reagents,
    check_for_rois,
    read_user_config,
)
from pyseq_core.reservation_system import ReservationSystem, reserve_microscope
from pyseq_core.roi_manager import ROIManager, read_roi_config
from typing import Dict, Union, List, Coroutine, Literal
from attrs import define, field
from pydantic import BaseModel, ValidationError
from pathlib import Path
import asyncio
import logging


LOGGER = logging.getLogger("PySeq")

DefaultPump = PumpCommandFactory(DEFAULT_CONFIG)


class PumpCommand(DefaultPump):
    pass


DefaultROI = BaseROIFactory(DEFAULT_CONFIG)


class ROI(DefaultROI):
    pass


DefaultSimpleStage = SimpleStageFactory(DEFAULT_CONFIG)


class SimpleStage(DefaultSimpleStage):
    pass


@define(kw_only=True)
class BaseSystem(ABC):
    name: str = field(default=None)
    instruments: dict = field(init=False)
    _queue: asyncio.Queue = field(factory=asyncio.Queue)
    _queue_dict: dict = field(factory=dict)
    _worker_task: asyncio.Task = field(init=False)
    _command_id: int = field(default=0)
    _config: dict = field(init=False)
    _current_task: asyncio.Task = field(default=None)
    _pause_event: asyncio.Event = field(init=False, factory=asyncio.Event)
    _loop_stop: bool = field(init=False, default=False)
    _reservation_system: ReservationSystem = field(init=False)
    _protocol_name: str = field(default="")
    _protocol_cycle: int = field(default=1)
    # _background_tasks: set = field(init=False, factory=set)

    def __attrs_post_init__(self):
        # Start async worker
        self._worker_task = asyncio.create_task(self._worker())

        # Clear pause event to initially pause queue
        self._pause_event.clear()

        # Getting System Settings
        self._config = HW_CONFIG

        # Call extra post initialization methods
        self.__extra_post_init__()

    def __extra_post_init__(self):
        pass

    async def _worker(self):
        """Worker function to process the queue."""

        while not self._loop_stop:
            # Wait if queue is paused
            await self._pause_event.wait()

            # Get task
            try:
                id, description, func, args, kwargs = await self._queue.get()
            except asyncio.CancelledError:
                LOGGER.info(f"{self.name} :: Shutting down")
                break

            if not self._queue_dict[id][1]:
                # Check if the task is cancelled
                LOGGER.debug(f"Task {id} :: {description} cancelled")
            else:
                # Run the task in the event loop

                # Start task
                LOGGER.debug(f"{self.name} :: Task {id} :: {description} started")
                task_name = "_".join([str(_) for _ in args])
                self._current_task = asyncio.create_task(
                    func(*args, **kwargs), name=task_name
                )

                try:
                    # Wait for the task to finish
                    await self._current_task
                    LOGGER.debug(f"{self.name} :: Task {id} :: {description} finished")
                except asyncio.CancelledError:
                    LOGGER.warning(
                        f"{self.name} :: Task {id} :: {description} cancelled"
                    )
                except Exception:
                    # Check the task status
                    task_exception = self._current_task.exception()
                    LOGGER.error(
                        f"{self.name} :: Task {id} :: {description}: {task_exception}"
                    )

            # Remove the task from the queue dict
            self._queue_dict.pop(id)
            self._queue.task_done()

        LOGGER.info(f"{self.name} :: Queue stopped")

    def add_task(self, description, func, *args, **kwargs):
        """Add a task to the queue."""

        id = self._command_id
        self._command_id += 1
        self._queue_dict.update({id: [description, True]})
        self._queue.put_nowait([id, description, func, args, kwargs])
        return id

    def cancel_task(self, command_id):
        """Cancel a task in the queue."""
        if command_id in self._queue_dict:
            self._queue_dict[command_id][1] = False
            description = self._queue_dict[command_id][0]
            LOGGER.info(f"Cancelled task {command_id} :: {description}")
        else:
            LOGGER.warning(f"Task {command_id} not found")

    async def clear_queue(self):
        for command_id in self._queue_dict:
            self.cancel_task(command_id)
        while self._queue.qsize() > 0:
            await self._queue.get()
            self._queue.task_done()

    def initialize(self):
        """Initialize the system."""
        description = f"Initialize {self.name}"
        self.add_task([description, self._initialize])

    def shutdown(self):
        """Shutdown the system."""
        description = f"Shutdown {self.name}"
        self.add_task([description, self._shutdown])

    def configure(self):
        """Configure the system."""
        description = f"Configure {self.name}"
        self.add_task([description, self._configure])

    def pause(self):
        """Pause the system queue."""
        LOGGER.info(f"Pausing {self.name}")
        self._pause_event.clear()

    def start(self):
        """Start or unpause the system queue."""
        LOGGER.info(f"Starting {self.name}")
        self._pause_event.set()

    @property
    def condition_lock(self):
        return self.reservation_system.condition_lock

    @property
    def reserved_for(self):
        return self.reservation_system.reserved_for

    @reserved_for.setter
    def reserved_for(self, flowcell: Union[str, None]):
        self.reservation_system.reserved_for = flowcell

    async def _check_pause_and_cancel(
        self, await_task: asyncio.Task, check_cancel: bool = True
    ):
        """Wait if pause event set or exit if current task canceled.
        Optionally if awaiting task is not done, cancel it.
        """

        await asyncio.wait([await_task, self._current_task], asyncio.FIRST_COMPLETED)
        await self.pause_event
        if check_cancel:
            if not self.await_task.done():
                await_task.cancel()

    @abstractmethod
    async def _initialize(self):
        """Initialize the system."""
        pass

    @abstractmethod
    async def _shutdown(self):
        """Shutdown the system."""
        pass

    @abstractmethod
    async def _configure(self, command):
        """Configure the system."""
        pass


@define(kw_only=True)
class BaseMicroscope(BaseSystem):
    name: str = field(default="microscope")
    lock_condition: asyncio.Lock = field(factory=asyncio.Lock)
    image_path: Dict[str, Path] = field(factory=dict)
    focus_path: Dict[str, Path] = field(factory=dict)

    @property
    def YStage(self) -> BaseYStage:
        """Abstract property for the YStage."""
        return self.instruments.get("YStage", None)

    @property
    def XStage(self) -> BaseXStage:
        """Abstract property for the XStage."""
        return self.instruments.get("XStage", None)

    @property
    def ZStage(self) -> BaseZStage:
        """Abstract property for the ZStage."""
        return self.instruments.get("ZStage", None)

    @property
    def ObjStage(self) -> BaseObjectiveStage:
        """Abstract property for the ObjStage."""
        return self.instruments.get("ObjStage", None)

    @property
    def Shutter(self) -> BaseShutter:
        """Abstract property for the Shutter."""
        return self.instruments.get("Shutter", None)

    @property
    def FilterWheel(self) -> Dict[str, BaseFilterWheel]:
        """Abstract property for the FilterWheel.
        Return a dictionary of FilterWheel with their respective laser color lines."""
        return self.instruments.get("FilterWheel", {})

    @property
    def Laser(self) -> Dict[str, BaseLaser]:
        """Abstract property for the lasers.
        Return a dictionary of lasers with their respective colors.
        """
        return self.instruments.get("Laser", {})

    @property
    def Camera(self) -> Dict[str, BaseCamera]:
        """Abstract property for the cameras.
        Return a dictionary of cameras with their respective names.
        """
        return self.instruments.get("Camera", {})

    @abstractmethod
    async def _capture(self, filename):
        """Capture an image and save it to the specified filename."""
        pass

    @abstractmethod
    async def _z_stack(self, start, nsteps, step_size):
        """Perform a z-stack acquisition."""
        pass

    @abstractmethod
    async def _scan(self, roi: ROI):
        """Perform a scan over the specified region of interest (ROI)."""
        pass

    @abstractmethod
    async def _expose_scan(self, roi: ROI):
        """Scan over the specified region of interest (ROI) with laser."""
        pass

    @abstractmethod
    async def _move(self, roi: ROI):
        """Move the stage ROI x,y,z coordinates."""
        pass

    @abstractmethod
    async def _set_parameters(self, image_params: Optics):
        """Async set the parameters for the ROI."""
        pass

    @abstractmethod
    async def _find_focus(self, roi: ROI):
        """Async set the parameters for the ROI."""
        # Reset stage to initial position after finding focus
        pass

    # def validate_stage(self, roi:ROI):
    #     """Validate stage positions parameters"""

    #     errors = []
    #     stage = roi.stage.model_dump()

    #     # Validate XYZ stage positions
    #     for s in ['XStage', 'YStage', 'ZStage']:
    #         for pos in ['init', 'last']:
    #             d = s[0].lower()
    #             try:
    #                 self.instruments[s](stage[f'{d}_{pos}'])
    #             except ValueError as e:
    #                 LOGGER.error(e)
    #                 errors.append(e)

    #     #Validate extra stage position beyond x,y,z
    #     errors = self.validate_extra_stage(roi, errors)

    #     n_errors = len(errors)
    #     if n_errors > 0:
    #         raise ValueError(f'Found {n_errors} stage errors for {roi.name}')

    # def validate_optics(self, optics: Optics):
    #     ('FilterWheel', 'filter'), []
    #     self.FilterWheel(optics.filter)
    #     self.Laser(optics.laser)
    #     self.Camera(optics.exposure)

    # @abstractmethod
    # def validate_extra_stage(self, roi: ROI, errors) -> list:
    #     pass

    # Reset stage to initial position after finding focus
    # pass

    @reserve_microscope
    async def _from_flowcell(
        self, routine: Literal["image", "focus", "expose"], roi: List[BaseModel]
    ):
        for r in roi:
            if routine in "imaging":
                await self._image(r)
            elif routine in "focus":
                await self._focus(r)
            elif routine in "expose":
                await self._expose(r)

    async def _focus(self, roi: ROI):
        """Async find focus on roi."""
        # Don't move stage, _find_focus should move stage based on focusing routine
        description = f"Set focus parameters for {roi.name}"
        self.add_task(description, self._set_parameters, roi.focus.optics)
        description = f"Finding focus for {roi.name}"
        self.add_task(description, self._find_focus, roi)
        await self._queue.join()

    async def _expose(self, roi: ROI):
        """Async expose the sample for a specified duration without imaging."""

        description = f"Move to {roi.name}"
        self.add_task(description, self._move, roi)
        description = f"Set expose parameters for {roi.name}"
        self.add_task(description, self._set_parameters, roi.expose.optics)
        description = f"Expose {roi.name}"
        self.add_task(description, self._expose_scan, roi)
        await self._queue.join()

    async def _image(self, roi: ROI) -> None:
        """Async image ROIs."""

        description = f"Move to {roi.name}"
        self.add_task(description, self._move, roi)
        if roi.image.z_init is None:
            description = f"Set focus parameters for {roi.name}"
            self.add_task(description, self._set_parameters, roi.focus.optics)
            description = f"Autofocusing on {roi.name}"
            self.add_task(description, self._find_focus, roi)
        description = f"Set image parameters for {roi.name}"
        self.add_task(description, self._set_parameters, roi.image.optics)
        description = f"Scan {roi.name}"
        self.add_task(description, self._scan, roi)
        await self._queue.join()  # Wait for queue to finish

    def move(self, stage: SimpleStage) -> None:
        """Move the stage ROI x,y,z coordinates."""
        description = f"Move x:{stage.x}, y:{stage.y}, z:{stage.z}"
        self.add_task(description, self._move, SimpleStage)

    def image(self, roi: ROI) -> None:
        """Acquire image from the specified region of interest (ROI)."""
        description = f"Scan {roi.name})"
        self.add_task(description, self._scan, roi)

    def expose(self, roi: ROI) -> None:
        """Expose the sample to light without imaging."""
        description = f"Expose {roi.name}"
        self.add_task(description, self._scan, roi)

    def focus(self, roi: ROI) -> None:
        """Autofocus on ROI."""
        description = f"Focusing on {roi.name}"
        self.add_task(description, self._find_focus, roi)

    def set_parameters(self, roi_params: Optics, mode) -> None:
        """Set the laser power, filters, exposure, imaging mode, etc. for a specified region of interest (ROI)."""
        description = "Setting parameters"
        self.add_task(description, self._set_parameters, roi_params)


@define(kw_only=True)
class BaseFlowCell(BaseSystem):
    _roi_to_microscope: Coroutine = field(init=False)
    reagents: dict = field(factory=dict)
    ROIs: dict = field(init=False, factory=dict)
    enabled: bool = True
    _exp_config: dict = field(default=None)

    @property
    def Pump(self) -> BasePump:
        """Abstract property for the pump."""
        return self.instruments.get("Pump", None)

    @property
    def Valve(self) -> BaseValve:
        """Abstract property for the pump."""
        return self.instruments.get("Valve", None)

    @property
    def TemperatureController(self) -> BaseTemperatureController:
        """Abstract property for the pump."""
        return self.instruments.get("TemperatureController", None)

    def select_port(self, reagent: Union[int, str]):
        """Select a port on the valve."""

        if isinstance(reagent, str):
            port = self.reagents[reagent]["port"]
        elif isinstance(reagent, int):
            port = reagent

        if self.Valve(port):
            description = f"Select {reagent} at port {port}."
            self.add_task(description, self._select_port, port)
            return True
        return False

    def pump(
        self,
        volume: Union[int, float],
        flow_rate: Union[int, float],
        reagent: Union[int, str] = None,
        reverse: bool = False,
        **kwargs,
    ) -> int:
        """Pump volume in uL from port at flow rate in uL/min."""

        if reagent is not None:
            if not self.select_port(reagent):
                raise KeyError(f"{reagent} is invalid for Valve {self.name}")

        if flow_rate is None:
            flow_rate = self.reagents[reagent].get("flow_rate")

        if self.Pump(volume, flow_rate):
            if not reverse:
                description = f"Pump {volume} uL at {flow_rate} uL/min."
                return self.add_task(
                    description, self._pump, volume, flow_rate, **kwargs
                )
            else:
                return self.reverse_pump(volume, flow_rate, **kwargs)

    def reverse_pump(
        self,
        volume: Union[int, float],
        flow_rate: Union[int, float],
        port: Union[int, str] = None,
        **kwargs,
    ) -> int:
        """Pump volume in uL from waste to port at flow rate in uL/min."""

        if port is not None:
            self.select_port(port)

        description = f"Reverse pump {volume} uL at {flow_rate} uL/min."
        return self.add_task(
            description, self._reverse_pump, volume, flow_rate, **kwargs
        )

    def hold(self, duration: Union[int, float]) -> int:
        """Hold for specified duration (minutes)."""
        description = f"Hold for {duration} minutes."
        # self.add_task(description, asyncio.sleep, duration*60)
        return self.add_task(description, self._hold, duration)

    def wait(self, event: str) -> int:
        """Wait for microscope or flowcell event."""
        description = f"Wait for {event}."
        return self.add_task(description, self._wait, event)

    def user(self, message: str, timeout: Union[int, float]) -> int:
        """Send message to the user and wait for a response."""
        description = "Wait for user response"
        return self.add_task(description, self._user_wait, message)

    def temperature(self, temperature: Union[int, float]) -> int:
        """Set the temperature of the flow cell."""
        description = f"Set temperature to {temperature} C"
        return self.add_task(description, self._temperature, temperature)

    async def _to_microscope(
        self,
        routine: Literal["image", "focus", "expose"],
        roi: Union[ROI, List[ROI]] = [],
    ):
        """Send ROIs to microscope to image, focus, or expose."""
        if not isinstance(roi, list):
            roi = [roi]
        if len(roi) == 0:
            roi = list(self.rois.values())
        await self._roi_to_microscope(routine, roi)

    def count_roi(self, roi: Union[ROI, List[ROI]] = []):
        if isinstance(roi, ROI):
            nROIs = 1
        else:
            nROIs = len(roi)
        if nROIs == 0:
            nROIs = len(self.ROIs)

    def image(self, roi: Union[ROI, List[ROI]] = []) -> int:
        """Image specified ROIs or all ROIs on flowcell (default)."""
        nROIs = self.count_roi(roi)
        description = f"Image {nROIs} ROIs"
        return self.add_task(description, self._to_microscope, "image", roi)

    def focus(self, roi: Union[ROI, List[ROI]] = []) -> int:
        """Focus on specified ROIs or all ROIs on flowcell (default)."""
        nROIs = self.count_roi(roi)
        description = f"Focus on {nROIs} ROIs"
        return self.add_task(description, self._to_microscope, "image", roi)

    def expose(self, roi: Union[ROI, List[ROI]] = []) -> int:
        """Expose specified ROIs or all ROIs on flowcell (default)."""
        nROIs = self.count_roi(roi)
        description = f"Expose {nROIs} ROIs"
        return self.add_task(description, self._to_microscope, "image", roi)

    def update_protocol_name(self, name: str):
        description = f"Notify user of new protocol {name}"
        self.add_task(description, self.update_protocol_name_task, name)

    def update_protocol_name_task(self, name: str):
        self._protocol_name = name
        LOGGER.info(f"Start protocol {name}")

    def update_protocol_cycle(self, cycle: int, total_cycles: int):
        description = f"Notify user new cycle {cycle}"
        self.add_task(description, self.update_protocol_cycle_task, cycle, total_cycles)

    def update_protocol_cycle_task(self, cycle: int, total_cycles: int):
        self._protocol_cycle = cycle
        if total_cycles > 1:
            LOGGER.info(
                f"Start {cycle}/{total_cycles} of protocol {self._protocol_name}"
            )

    async def _hold(self, duration):
        """Async hold for specified duration in minutes."""

        await asyncio.sleep(duration * 60)

    async def _wait(self, event: str):
        """Async wait for an event"""

        if event == "microscope":
            async with self.condition_lock:
                await self.condition_lock.wait_for(self.reserved_for is None)
            self.reserved_for(self.name)

    async def _user_wait(self, message, timeout=None):
        """Async send message to the user and wait for a response."""

        await asyncio.wait_for(asyncio.to_thread(input, message), timeout)

    @abstractmethod
    async def _temperature(self, temperature):
        """Set the temperature of the flow cell."""
        pass

    @abstractmethod
    async def _select_port(self, port):
        pass

    @abstractmethod
    async def _pump(self, volume, flow_rate, **kwargs):
        """Async pump a specified volume of a reagant at a specified flow rate."""
        pass

    @abstractmethod
    async def _reverse_pump(self, volume, flow_rate, **kwargs):
        """Async pump a specified volume of a reagant at a specified flow rate."""
        pass


@define
class BaseSequencer(BaseSystem):
    _microscope: BaseMicroscope = field(init=False)
    _flowcells: dict[Union[str, int], BaseFlowCell] = field(init=False)
    _reagents_manager: ReagentsManager = field(init=False)
    _roi_manager: ROIManager = field(init=False)

    @property
    def microscope(self) -> BaseMicroscope:
        """Abstract property for the microscope."""
        return self._microscope

    @property
    def flowcells(self) -> Dict[str, BaseFlowCell]:
        """Abstract property for the flow cells.
        Return a dictionary of flow cells with their respective names.
        """
        return self._flowcells

    def __extra_post_init__(self):
        # Set up microscope reservation system
        rez_sys = ReservationSystem()
        self._microscope._reservation_system = rez_sys

        # Add reagents manager
        self._reagents_manager = ReagentsManager(self._flowcells)

        # Add ROI manager
        self._roi_manager = ROIManager(self._flowcells)

        # Connect microscope to flow cells
        for fc in self._flowcells.keys():
            self._flowcells[fc]._roi_to_microscope = self._microscope._from_flowcell
            self._flowcells[fc]._reservation_system = rez_sys

        self._pause_event.set()

    @abstractmethod
    @_flowcells.default
    def set_flowcells(self):
        pass

    def pump(
        self,
        flowcells: Union[str, int] = None,
        pump_command: PumpCommand = None,
        **kwargs,
    ):
        """Pump volume in uL from/to specified port at flow rate in ul/min on specified flow cell."""
        fc_ = self._get_fc_list(flowcells)

        for fc in fc_:
            if pump_command is None:
                kwargs.update({"flowcell": fc})
                pump_command = PumpCommand(**kwargs)
            self._flowcells[fc].pump(**pump_command.model_dump())

    def hold(
        self,
        flowcells: Union[str, int] = None,
        hold_command: HoldCommand = None,
        **kwargs,
    ) -> Union[int, List[int]]:
        """Hold specified flow cell for specified duration in minutes, used for incubations."""

        if hold_command is None:
            hold_command = HoldCommand(**kwargs)
        fc_ = self._get_fc_list(flowcells)
        task_ids = []
        for fc in fc_:
            task_ids.append(self._flowcells[fc].hold(hold_command.duration))
        return task_ids

    def wait(
        self,
        flowcells: Union[str, int] = None,
        wait_command: WaitCommand = None,
        **kwargs,
    ) -> Union[int, List[int]]:
        """Specified flow cell waits for microscope before continuing."""

        if wait_command is None:
            wait_command = WaitCommand(**kwargs)
        fc_ = self._get_fc_list(flowcells)
        task_ids = []
        for fc in fc_:
            task_ids.append(self._flowcells[fc].wait(wait_command.event))
        return task_ids

    def temperature(
        self,
        flowcells: Union[str, int] = None,
        temperature_command: TemperatureCommand = None,
        **kwargs,
    ):
        """Hold specified flow cell for specified duration in minutes, used for incubations."""
        fc_ = self._get_fc_list(flowcells)
        for fc in fc_:
            if temperature_command is None:
                kwargs.update({"flowcell": fc})
                temperature_command = TemperatureCommand(**kwargs)
            self._flowcells[fc].temperature(temperature_command.temperature)

    def _roi_to_microscope(
        self,
        routine: Literal["image", "focus", "expose"],
        roi: Union[ROI, List[ROI]] = [],
        flowcells: Union[str, List[str]] = None,
    ):
        if roi is None and flowcells is not None:
            for fc in self._get_fc_list(flowcells):
                _fc = self._flowcells[fc]
                _fc._to_microscope(routine, list(_fc._rois.items()))
            return
        elif roi is None and flowcells is None:
            raise ValueError("Specify at least 1 flow cell")
        else:
            if not isinstance(roi, list):
                roi = [roi]
            for r in roi:
                self._flowcells[r.stage.flowcell]._to_microscope(routine, r)

    def image(
        self,
        roi: Union[ROI, List[ROI]] = [],
        flowcells: Union[str, List[str]] = None,
        **kwargs,
    ):
        """Image ROIs."""

        if len(roi) == 0 and flowcells is None:
            roi = [ROI(**kwargs)]
        self._roi_to_microscope("image", roi, flowcells)

    def focus(
        self, roi: Union[ROI, List[ROI]], flowcells: Union[str, List[str]] = None
    ):
        """Find focus z position in ROIs."""
        self._roi_to_microscope("focus", roi, flowcells)

    def expose(
        self,
        roi: Union[ROI, List[ROI]],
        flowcells: Union[str, List[str]] = None,
        **kwargs,
    ):
        """Expose ROIs to light without imaging."""
        if len(roi) == 0 and flowcells is None:
            roi = [ROI(**kwargs)]
        self._roi_to_microscope("expose", roi, flowcells)

    def pause(self, queues: Union[str, List[str]] = None):
        """Pause flow cell, microscope, or entire sequencer (default)."""

        # Check user supplied queues
        queues = self._get_systems_list(queues)
        for q in queues:
            q.pause()

    def start(self, queues: Union[str, List[str]] = None):
        """Start flow cell, microscope, or entire sequencer (default)."""

        # Check user supplied queues
        queues = self._get_systems_list(queues)
        for q in queues:
            q.start()

    def _get_systems_list(self, systems: Union[str, List[str]] = None):
        """Return list of valid flow cell and microscope systems."""

        fc_list = self._get_fc_list()
        microscope = self._microscope.name

        if systems is None:
            systems = fc_list + [microscope]
        elif isinstance(systems, str):
            systems = [systems]

        systems_ = []
        for i in systems:
            if i in fc_list:
                systems_.append(self.flowcells[i])
            elif i in microscope:
                systems_.append(self.microscope)
            else:
                raise ValueError(f"{i} is not a valid flow cell or microscope.")

        return systems_

    def _get_fc_list(self, fc: Union[str, list] = None):
        """Return list of valid flowcells."""

        valid_fc = list(self._flowcells.keys())
        if fc is None:
            fc_ = valid_fc
            return list(fc_)
        elif isinstance(fc, str) and len(fc) == 1:
            fc_ = [fc]
        fc_ = [_.upper() for _ in fc]

        # Check user supplied flow cell names
        for fc in fc_:
            if fc not in valid_fc:
                raise ValueError(f"{fc} is not a valid flow cell.")

        return fc_

    def _enable(self, fc_dict: Dict[str, bool], *args: str):
        """Enable specified flowcells."""
        if len(fc_dict) == 0 and len(args) > 0:
            for fc in args:
                fc = fc.upper()
                if fc not in self._flowcells:
                    LOGGER.warning(f"Flowcell {fc} not found in sequencer")
                else:
                    fc_dict[fc] = True

    def disable(self, fc_dict: Dict[str, bool], *args: str):
        """Disable specified flowcells"""
        if len(fc_dict) == 0 and len(args) > 0:
            for fc in args:
                fc = fc.upper()
                if fc.upper() not in self._flowcells:
                    LOGGER.warning(f"Flowcell {fc} not found in sequencer")
                else:
                    fc_dict[fc.upper()] = False
        self.enable(fc_dict)

    @property
    def enable(self):
        """Get the enabled status of the flowcells."""
        return self._enable

    @enable.setter
    def enable(self, flowcells: str):
        """Enable specified flowcells."""
        self._enable = {fc.upper(): True for fc in self._get_fc_list(flowcells)}

    @property
    def enabled(self):
        """Get the enabled status of the flowcell."""

        return [fc for fc in self._flowcells if self._flowcells[fc].enable]

    def add_rois(self, flowcells, roi_path: str) -> int:
        flowcells = self._get_fc_list(flowcells)

        # Read roi file and get list of validated ROIs
        try:
            rois = read_roi_config(
                flowcells,
                roi_path,
                self.flowcells[flowcells[0]]._exp_config,
                self.custom_roi_factory,
            )
        except ValidationError as e:
            LOGGER.error(e)
            return 0

        # Add rois to flowcells
        for roi in rois:
            self._roi_manager.add(roi)
        # Wake up flowcells waiting for ROIs
        if self._roi_manager.roi_condition.locked():
            self._roi_manager.roi_condition.notify_all()

        return len(rois)

    async def new_experiment(self, flowcells: str, exp_config_path: str):
        flowcells = self._get_fc_list(flowcells)
        for fc in flowcells:
            if not self.flowcells[fc]._queue.empty():
                raise RuntimeError(
                    f"Flow cell {fc.name} still running, stop flow cell before starting new experiment"
                )
            else:
                self.flowcells[fc].pause()

        # Read experiment config
        exp_config = read_user_config(exp_config_path)

        # Set up paths for imaging & focusing. Reset rois and reagents
        image_path = Path(exp_config["experiment"].get("image_path", "."))
        focus_path = Path(exp_config["experiment"].get("focus_path", image_path))
        image_path.mkdir(parents=True, exist_ok=True)
        focus_path.mkdir(parents=True, exist_ok=True)
        for fc in flowcells:
            self.flowcells[fc]._exp_config = exp_config
            self.flowcells[fc].ROIs = dict()
            self.flowcells[fc].reagents = dict()
            self.microscope.image_path[fc] = image_path
            self.microscope.focus_path[fc] = focus_path

        # Add reagents from experiment config to flowcells
        for fc in flowcells:
            self._reagents_manager.add_from_config(fc, exp_config)

        # Add ROIs from experiment config to flowcels
        roi_path = Path(exp_config["experiment"].get("roi_path", "."))
        if roi_path.is_file():
            LOGGER.info(f"Adding ROIs from {roi_path}")
            n_rois_added = self.add_rois(flowcells, roi_path)
            LOGGER.info(f"Added {n_rois_added} ROIs")

        # Read protocol from experiment config
        protocol = read_protocol(exp_config["experiment"]["protocol_path"])
        fprotocol = {}
        for fc in flowcells:
            protocol = read_protocol(exp_config["experiment"]["protocol_path"])
            fprotocol[fc] = format_protocol(fc, protocol, exp_config)

        # Check if reagents are needed
        for fc in flowcells:
            missing_reagents = need_reagents(fprotocol[fc], self.flowcells[fc].reagents)
            if missing_reagents > 0:
                raise ValueError(
                    f"Missing {missing_reagents} reagents for flowcell {fc}"
                )

        # Check if ROIs needed -> wait for ROIs if none in config
        for fc in flowcells:
            if not check_for_rois(fprotocol[fc]) and len(self.flowcells[fc].ROIs) == 0:
                await self._roi_manager.wait_for_rois(fc)

        # Add steps from protocol to queues
        for fc in flowcells:
            self.queue_protocol(fc, fprotocol[fc])

    def queue_protocol(self, flowcell: Union[str, int], fprotocols: dict):
        for pname, protocol in fprotocols.items():
            LOGGER.info(f"Queueing protocol {pname} on flowcell {flowcell}")
            self.flowcells[flowcell].update_protocol_name(pname)
            for cycle in range(protocol["cycles"]):
                self.flowcells[flowcell].update_protocol_cycle(
                    cycle + 1, protocol["cycles"]
                )
                for step in protocol["steps"]:
                    LOGGER.debug(f"Added {step[0]}, {step[1]} on flowcell {flowcell}")
                    params = step[1]
                    if "PUMP" in step[0]:
                        self.pump(flowcells=flowcell, **params)
                    elif "HOLD" in step[0]:
                        self.hold(flowcells=flowcell, **params)
                    elif "WAIT" in step[0]:
                        self.wait(flowcells=flowcell, event=params["event"])
                    elif "USER" in step[0]:
                        self.user(flowcells=flowcell, **params)
                    elif "IMAG" in step[0]:
                        self.image(flowcells=flowcell, **params)
                    elif "EXPO" in step[0]:
                        self.expose(flowcells=flowcell, **params)

    @abstractmethod
    def custom_roi_factory(name: str, flowcell: Union[str, int], **kwargs) -> ROI:
        pass
