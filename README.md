# pyseq_core
Core functions and base classes for pyseq


## Prerequsites
1. git https://git-scm.com/
2. uv https://docs.astral.sh/uv/

## Install 
1. Clone repo (git clone)
2. uv sync 
3. uv run pre-commit install 


### Data Structure
- Use params to format data such as imaging, regions of interests, or pumping parameters, etc. See src/base_protocol.py

### Instruments
- Inherit specific instrument abstract base class
- Add communication protocol by composition
- All methods that communicate with instrument should be async

### Systems
- Flowcells -> Pumps, Valves, Temperature Controller
- Microscope -> Stages, Cameras, Lasers, any optics such as Shutters/Filters
- Sequencer -> Flowcells & Microscopes
- Async high level commands for pumping, imaging, synchronizing
- Format async commands with _
- Use wrappers around async commands too add a task to the queue
- System queues are FIFO, tasks have ids, and queues can be edited and paused
- Tasks in queues can be reordered and deleted but not modified

### Hardware Settings
- Hardware settings that can't be or shouldn't be changed easily should go in machine_settings.yaml

### Experiment & Software Settings
- Experiment/software settings that need to be changed easily should go default_config.toml
- Experiment settings should mimic ROI stage, focusing, imaging, and exposing parameters
- Reagents specified in seperate toml section [method.reagent] {reagent_name: port}
- Reagents should follow reagents parameters, with default flow rates, pause, etc from [method.fluidics]

### Recipes
- Recipes follow simple yaml flow style and then formatted into more structured and annotated yaml

### ROIs
- Can fully define stage and image parameters in recipe.
- If only image parameters in recipe, all ROIs defined for flowcell will be imaged with these parameters
- Default image parameters can be defined in experiment config
