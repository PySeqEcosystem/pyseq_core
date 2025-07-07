from typing import Union
from attrs import define, field
from warnings import warn
from pydantic import BaseModel, create_model, model_validator
from pyseq_core.utils import HW_CONFIG
from pyseq_core.base_protocol import (
    validate_in,
    validate_min_max,
    custom_params,
    recursive_validate,
)
import logging

LOGGER = logging.getLogger("PySeq")


class BaseReagent(BaseModel):
    flowcell: Union[str, int]
    name: str
    port: int
    flow_rate: Union[int, float]

    @model_validator(mode="after")
    def validate_port_flowrate(self):
        validate_in(HW_CONFIG[f"Valve{self.flowcell}"]["valid_list"], self.port)
        validate_min_max("flow_rate", self.flow_rate, HW_CONFIG[f"Pump{self.flowcell}"])
        return self


@define
class ReagentsManager:
    """Class to manage adding, editing, and removing reagents from flowcells."""

    flowcells: dict = field()

    def reagents(self, flowcell: Union[str, int]) -> dict:
        return self.flowcells[flowcell].reagents

    def get_reagent_key(self, flowcell: Union[str, int], port: int) -> str:
        """Get reagent name/key by port number, return empty string if not found."""
        reagents = self.reagents(flowcell)
        key = list(filter(lambda k: reagents[k]["port"] == port, reagents))
        if len(key) > 1:
            raise ValueError(
                f"More than 1 reagent mapped to port {port} on flowcell {flowcell}"
            )
        return "".join(key)

    def check_port(self, flowcell: Union[str, int], reagent: BaseReagent) -> bool:
        """Check reagent name and port number not already used."""

        # Check reagent name is not already listed
        reagents = self.reagents(flowcell)
        if reagent.name in reagents:
            port = reagents[reagent.name]["port"]
            warn(
                f"Duplicate Port: {reagent.name} already mapped to port {port} on flowcell {flowcell}",
                UserWarning,
            )
            return False

        # Check port not used by another reagent
        existing_reagent = self.get_reagent_key(flowcell, reagent.port)
        if len(existing_reagent) > 0:
            warn(
                f"Duplicate Port: Port {reagent.port} is already used by {existing_reagent} on flowcell {flowcell}",
                UserWarning,
            )
            return False

        return True

    def check_flow_rate(
        self, flowcell: Union[str, int], flow_rate: Union[int, float]
    ) -> bool:
        """Check reagent flow rate"""
        # Validate flow rates
        return self.flowcells[flowcell].Pump(flow_rate=flow_rate)

    def add(self, reagent: BaseReagent = None, **kwargs):
        """Add reagent to flowcell."""

        if reagent is None:
            reagent = BaseReagent(**kwargs)

        flowcell = reagent.flowcell
        # Add reagent if both port and reagent name are not already used
        if self.check_port(flowcell, reagent):
            LOGGER.info(f"Added reagent {reagent.name}")
            LOGGER.debug(f"{reagent}")
            self.reagents(flowcell)[reagent.name] = reagent.model_dump()

        return self.reagents(flowcell)

    def update(self, reagent: BaseReagent = None, **kwargs) -> dict:
        """Update exisiting reagent parameters."""

        if reagent is None:
            assert "name" in kwargs, "name must be specified"
            assert "flowcell" in kwargs, "flowcel must be specified"
            flowcell = kwargs["flowcell"]
            if kwargs["name"] in self.flowcells[flowcell].reagents:
                reagent = self.flowcells[flowcell].reagents[kwargs["name"]].copy()
                reagent.update(**kwargs)
            elif "port" in kwargs:
                old_name = self.get_reagent_key(flowcell, kwargs["port"])
                if len(old_name) > 0:
                    reagent = self.flowcells[flowcell].reagents[old_name].copy()
                    reagent.update(**kwargs)
                else:
                    ValueError(f"No existing reagent with port {kwargs['port']}")
            else:
                raise ValueError(f"Invalid reagent name {kwargs['name']}")

        if isinstance(reagent, BaseReagent):
            reagent = reagent.model_dump()

        flowcell = reagent["flowcell"]
        reagents = self.reagents(flowcell)
        reagent_name = self.get_reagent_key(flowcell, reagent["port"])
        if len(reagent_name) == 0:
            reagent_name = reagent["name"]

        # Update reagent name
        if reagent_name != reagent["name"]:
            filter_names = [k for k in reagents.keys() if k != reagent_name]
            if reagent["name"] not in filter_names:
                # new name does not match existing reagent
                reagent_values = reagents.pop(reagent_name)  # remove old name
                reagent_values["name"] = reagent["name"]  # update to new name
                reagents[reagent["name"]] = reagent_values  # add reagent with new name
                reagent_name = reagent["name"]
            else:
                # new name matches existing reagent
                port = reagents[reagent["name"]]
                warn(
                    f"Duplicate Port: {reagent['name']} already mapped to port {port} on flowcell {flowcell}",
                    UserWarning,
                )

        # Update port
        if reagents[reagent_name]["port"] != reagent["port"]:
            # check if port used by another reagent
            existing_reagent = self.get_reagent_key(flowcell, reagent["port"])
            if len(existing_reagent) == 0:  # or existing_reagent == reagent['name']:
                reagents[reagent_name].update({"port": reagent["port"]})  # update port

        # Update flowrate
        if reagents[reagent_name]["flow_rate"] != reagent["flow_rate"]:
            if self.check_flow_rate(flowcell, reagent["flow_rate"]):
                reagents[reagent_name].update({"flow_rate": reagent["flow_rate"]})

        # Update other parameter, no check though
        del reagent["port"]
        del reagent["flow_rate"]
        del reagent["name"]
        del reagent["flowcell"]
        reagents[reagent_name].update(reagent)

        return reagents

    def remove(self, flowcell: Union[str, int], reagent_name: str) -> dict:
        reagents = self.reagents(flowcell)

        if reagent_name in reagents:
            del reagents[reagent_name]

        return reagents

    def add_from_config(self, flowcell: Union[str, int], config: dict):
        # Custom Reagent class with extra pump parameters
        ExtraPumpParams = create_model(
            "ExtraPumpParams", **custom_params(config["pump"])
        )

        class Reagent(ExtraPumpParams, BaseReagent):
            @model_validator(mode="after")
            def validate_pump_params(self):
                recursive_validate(self.model_dump(), HW_CONFIG[f"Pump{flowcell}"])
                return self

        for name, params in config["reagents"].items():
            if isinstance(params, int):
                # reagent_name: port number
                params = {"flowcell": flowcell, "name": name, "port": params}
            elif isinstance(params, dict):
                # reagent_name: {port: port_number, flow_rate: flow_rate, ...}
                params.update({"name": name, "flowcell": flowcell})
            reagent = Reagent(**params)
            self.add(reagent)
