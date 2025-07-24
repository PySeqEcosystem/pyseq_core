import pytest
import importlib
from shutil import copyfile
import tomlkit


@pytest.mark.asyncio
async def test_protocol(BaseTestSequencer, tmp_path):
    # Read test experiment configuration
    resource_path = importlib.resources.files("pyseq_core") / "resources"
    exp_file = "test_experiment.toml"
    exp_path = resource_path / "test_experiment.toml"
    exp_conf = tomlkit.parse(open(exp_path).read())
    exp_name = exp_conf["experiment"]["name"]
    exp_conf["ROTATE_LOGS"] = True

    # Update paths in experiment configuration
    protocol_file = "test_protocol.yaml"
    roi_file = "test_roi.toml"
    exp_conf["experiment"]["output_path"] = str(tmp_path)
    exp_conf["experiment"]["protocol_path"] = str(tmp_path / protocol_file)
    exp_conf["experiment"]["roi_path"] = str(tmp_path / roi_file)

    # Write updated experiment and protocol/rois to temp directory
    with open(tmp_path / exp_file, "w") as f:
        tomlkit.dump(exp_conf, f)
    copyfile(resource_path / protocol_file, tmp_path / protocol_file)
    copyfile(resource_path / roi_file, tmp_path / roi_file)

    BaseTestSequencer.new_experiment(["A", "B"], tmp_path / exp_file, exp_name)
    await BaseTestSequencer._queue.join()

    # Check paths are created
    assert (tmp_path / exp_name).exists()
    paths = ["images", "focus", "log"]
    for p in paths:
        assert (tmp_path / exp_name / p).exists()
    assert (tmp_path / exp_name / f"log/{exp_name}.log").exists()

    # Check protocol is queued
    assert len(BaseTestSequencer.flowcells["A"]._queue_dict) > 0
    assert len(BaseTestSequencer.flowcells["B"]._queue_dict) > 0

    # Check rois are loaded
    assert len(BaseTestSequencer.flowcells["A"].ROIs) > 0
    assert len(BaseTestSequencer.flowcells["B"].ROIs) > 0

    # Check reagents are loaded
    assert len(BaseTestSequencer.flowcells["A"].reagents) > 0
    assert len(BaseTestSequencer.flowcells["B"].reagents) > 0

    # Clear Queue and start flowcells for clean teardown
    await BaseTestSequencer.flowcells["A"].clear_queue()
    await BaseTestSequencer.flowcells["B"].clear_queue()
    await BaseTestSequencer.microscope.clear_queue()
    await BaseTestSequencer.clear_queue()
