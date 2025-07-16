from asyncio import Condition
from attrs import define, field
from pydantic import BaseModel
from typing import Union, List
import logging

LOGGER = logging.getLogger("PySeq")


@define
class ReservationSystem:
    """Store name for reservation and lock seat."""

    reserved_for: str = field(default=None)
    condition_lock: Condition = field(factory=Condition)


def reserve_microscope(func):
    """Wrapper to reserve the microscope for a flow cell."""

    async def wrap(self, routine: str, roi: Union[BaseModel, List[BaseModel]]):
        if not isinstance(roi, list):
            roi = [roi]
        flowcell = roi[0].stage.flowcell

        def check_reservation():
            """Check reservation matches the flowcell requesting the microscope"""
            if self.reserved_for is None:
                LOGGER.debug(f"{self.name} not reserved, walk in seat for {flowcell}")
                self.reserved_for = flowcell
                return True
            else:
                LOGGER.debug(f"{flowcell} requesting seat for {self.name}")
                LOGGER.debug(f"{self.name} reserved for {flowcell}")
                return self.reserved_for == flowcell

        async with self.condition_lock:
            # Wait for seat
            await self.condition_lock.wait_for(check_reservation)

            # Use microscope
            LOGGER.debug(f"{flowcell} using {self.name}.")
            await func(self, routine, roi)

            # Clear Reservation
            LOGGER.debug(f"Clearing reservation for {flowcell} on {self.name}.")
            self.reserved_for = None
            self.condition_lock.notify_all()

    return wrap
