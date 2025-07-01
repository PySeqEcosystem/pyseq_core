
from __future__ import annotations
from attrs import define, field
from pyseq_core.base_protocol import BaseROIFactory
from pyseq_core.utils import DEFAULT_CONFIG# #HW_CONFIG, deep_merge

from warnings import warn
# from abc import abstractmethod
# from pydantic import ValidationError
from typing import Union, Callable, Any, TYPE_CHECKING
import logging
import tomlkit
from asyncio import Condition

if TYPE_CHECKING:
    from pyseq_core.base_system import BaseMicroscope

LOGGER = logging.getLogger('PySeq')



_DefaultROI = BaseROIFactory(DEFAULT_CONFIG)
class DefaultROI(_DefaultROI):
    pass



def read_roi_config(flowcells: str, 
                    config_path: str, 
                    exp_config: dict = None,
                    custom_roi_factory: Callable[[str, Union[int, str], Any], DefaultROI] = None) -> list[DefaultROI]:
    """Read ROI toml file and return list of ROIs.

        TOML file can be in any of the following forms

        [flowcell]
        roi_name: {custom roi kwargs}
        ---
        [roi_name]:
        flowcell: fc
        custom roi kwarg: kwarg
        ---
        [roi_name]:
        stage: stage kwargs
        image: {optics: optics kwargs, **image kwargs}
        focus: {optics: optics kwargs, **focus kwargs}
        expose: {optics: optics kwargs, **expose kwargs}

        Can pass custom_roi_factory callable to parse kwargs and return ROI.

    """
    
    roi_config = tomlkit.parse(open(config_path).read())

    if exp_config is not None: 
        ROI = BaseROIFactory(exp_config)
    else:
        ROI = DefaultROI

    rois = []
    for roi_name, _roi in roi_config.items():
        fc = _roi.get('flowcell', None)
        if roi_name in flowcells and fc is None:
            #{flowcell: {roi_name: **custom_roi_kwargs}
            fc = roi_name
            for roi_name_, roi_ in _roi.items():
                rois.append(custom_roi_factory(name=roi_name_, flowcell=fc, **roi_))
        elif fc is not None and fc in flowcells:
            #{roi_name: {flowcell: fc, **custom_roi_kwargs}
            rois.append(custom_roi_factory(name=roi_name, **_roi))
        else:
            #{roi_name: name, stage: **stage_kwargs, image:**image_kwargs, ...}
            rois.append(ROI(name=roi_name, **_roi))
    return rois



@define
class ROIManager():
    flowcells: dict = field(factory=dict)
    microscope: BaseMicroscope = field(init=False)
    roi_condition: Condition = field(factory=Condition)

    def rois(self, flowcell:str) -> dict:
        return self.flowcells[flowcell].ROIs
    
    def add(self, roi: DefaultROI = None, exp_config:dict = None, **kwargs):

        if exp_config is not None: 
            ROI = BaseROIFactory(exp_config)
        else:
            ROI = DefaultROI

        if roi is None:
            roi = ROI(**kwargs)
            # self.microscope.validate_ROI(roi)
        fc = roi.stage.flowcell
        if roi.name not in self.rois(fc):
            self.rois(fc)[roi.name] = roi
            LOGGER.info(f'Added {roi.name} to flowcell {fc}')
            LOGGER.debug(f'{roi}')
        else:
            msg = f'{roi.name} already exists on flowcell {fc}'
            LOGGER.warning(msg)
            warn(msg, UserWarning)

    def update(self, roi: DefaultROI):
        fc = roi.stage.flowcell
        if roi.name in self.rois(fc):
            LOGGER.debug(f'{self.rois(fc)[roi.name]}')
            self.rois(fc)[roi.name] = roi
            LOGGER.info('Updated {roi.name} on flowcell {fc}')
            LOGGER.debug(f'{roi}')
        else:
            msg = f'{roi.name} does not exist on flowcell {fc}'
            LOGGER.warning(msg)
            warn(msg, UserWarning)

    def remove(self, flowcell: str, roi: str):
        if roi in self.rois(flowcell):
            del self.rois(flowcell)[roi]

    async def wait_for_rois(self, flowcell:str):
        with self.roi_condition: 
            LOGGER.info(f'Waiting for ROIs on flowcell {flowcell}')
            self.roi_condition.wait_for(self.rois(flowcell) > 0)
            LOGGER.info(f'{len(self.rois(flowcell))} ROIs on flowcell {flowcell}')
