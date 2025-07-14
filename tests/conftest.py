import pytest_asyncio
import pytest
import importlib


# Base Test Sequencer
@pytest_asyncio.fixture
async def BaseTestSequencer():
    """Uninitialized Base Test Sequencer with only default settings."""
    from sequencers import test_sequencer

    seq = test_sequencer.TestSequencer(name="Test")
    seq.start()
    # return  seq

    yield seq

    # Sequencer Teardown

    # Stop loops
    seq.flowcells["A"]._loop_stop = True
    seq.flowcells["B"]._loop_stop = True
    seq.microscope._loop_stop = True
    seq._loop_stop = True

    # Cancel worker
    seq.flowcells["A"]._worker_task.cancel()
    seq.flowcells["B"]._worker_task.cancel()
    seq.microscope._worker_task.cancel()
    seq._worker_task.cancel()

    await seq.flowcells["A"]._worker_task
    await seq.flowcells["B"]._worker_task
    await seq.microscope._worker_task
    await seq._worker_task


@pytest.fixture
def test_roi_file_path():
    """Path to test_roi.toml in resources.

    Lists the following ROIs and specifies 1 z plane to image
    flowcell A: roi1A, roi2, roi3
    flowcell B: roi1B, roi2, roie

    """
    resource_path = importlib.resources.files("pyseq_core") / "resources"
    return resource_path / "test_roi.toml"


@pytest.fixture
def BaseTestSequencerROIs(BaseTestSequencer, test_roi_file_path):
    """Base Test sequencer loaded with ROIs from test_roi.toml."""
    BaseTestSequencer.add_rois("AB", test_roi_file_path)
    return BaseTestSequencer
