import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def BaseTestSequencerWithReagents(BaseTestSequencer):
    for fc in ["A", "B"]:
        BaseTestSequencer._reagents_manager.add(
            flowcell=fc, name="PBS", port=1, flow_rate=500
        )
        BaseTestSequencer._reagents_manager.add(
            flowcell=fc, name="water", port=2, flow_rate=500
        )
        BaseTestSequencer._reagents_manager.add(
            flowcell=fc, name="temp", port=3, flow_rate=500
        )
    BaseTestSequencer._reagents_manager.add(
        flowcell=fc, name="test", port=4, flow_rate=100
    )

    return BaseTestSequencer


def test_add_reagent(BaseTestSequencer):
    for fc in ["A", "B"]:
        BaseTestSequencer._reagents_manager.add(
            flowcell=fc, name="PBS", port=1, flow_rate=500
        )
        BaseTestSequencer._reagents_manager.add(
            flowcell=fc, name="water", port=2, flow_rate=500
        )
        BaseTestSequencer._reagents_manager.add(
            flowcell=fc, name="temp", port=3, flow_rate=500
        )
    BaseTestSequencer._reagents_manager.add(
        flowcell=fc, name="test", port=4, flow_rate=100
    )

    assert len(BaseTestSequencer.flowcells["A"].reagents) == 3
    assert len(BaseTestSequencer.flowcells["B"].reagents) == 4


@pytest.mark.filterwarnings("ignore:Duplicate Port")
def test_add_negcntrl(BaseTestSequencerWithReagents):
    # Negative controls, reagents should not be added to flow cell

    # Try to add reagent with dupliciate name
    BaseTestSequencerWithReagents._reagents_manager.add(
        flowcell="A", name="temp", port=5, flow_rate=100
    )
    # Try to add reagent with dupliciate port
    BaseTestSequencerWithReagents._reagents_manager.add(
        flowcell="B", name="test1", port=4, flow_rate=100
    )

    assert len(BaseTestSequencerWithReagents.flowcells["A"].reagents) == 3
    assert len(BaseTestSequencerWithReagents.flowcells["B"].reagents) == 4


def test_update_reagent_flowrate(BaseTestSequencerWithReagents):
    # Update flow_rate
    BaseTestSequencerWithReagents._reagents_manager.update(
        flowcell="B", name="test", flow_rate=200
    )
    assert (
        BaseTestSequencerWithReagents.flowcells["B"].reagents["test"]["flow_rate"]
        == 200
    )


def test_update_reagent_name(BaseTestSequencerWithReagents):
    # Update name
    BaseTestSequencerWithReagents._reagents_manager.update(
        flowcell="B", name="test1", port=4
    )
    assert BaseTestSequencerWithReagents.flowcells["B"].reagents["test1"]["port"] == 4
    assert len(BaseTestSequencerWithReagents.flowcells["B"].reagents) == 4
    assert "test" not in BaseTestSequencerWithReagents.flowcells["B"].reagents


def test_update_reagent_port(BaseTestSequencerWithReagents):
    # Update port
    BaseTestSequencerWithReagents._reagents_manager.update(
        flowcell="B", name="test", port=5
    )
    assert BaseTestSequencerWithReagents.flowcells["B"].reagents["test"]["port"] == 5
    assert len(BaseTestSequencerWithReagents.flowcells["B"].reagents) == 4


@pytest.mark.filterwarnings("ignore:Duplicate Port")
def test_update_negcntrl(BaseTestSequencerWithReagents):
    # Negative controls, reagents should not be added to flow cell

    # Negative control, change port to occupied port
    BaseTestSequencerWithReagents._reagents_manager.update(
        flowcell="B", name="test", port=1
    )
    assert BaseTestSequencerWithReagents.flowcells["B"].reagents["test"]["port"] == 4
    assert BaseTestSequencerWithReagents.flowcells["B"].reagents["PBS"]["port"] == 1
    assert len(BaseTestSequencerWithReagents.flowcells["B"].reagents) == 4

    # Negative control, change name to existing reagent
    BaseTestSequencerWithReagents._reagents_manager.update(
        flowcell="B", name="temp", port=4
    )
    assert BaseTestSequencerWithReagents.flowcells["B"].reagents["test"]["port"] == 4
    assert BaseTestSequencerWithReagents.flowcells["B"].reagents["temp"]["port"] == 3
    assert len(BaseTestSequencerWithReagents.flowcells["B"].reagents) == 4


def test_remove_reagent(BaseTestSequencerWithReagents):
    BaseTestSequencerWithReagents._reagents_manager.remove(
        flowcell="A", reagent_name="temp"
    )
    BaseTestSequencerWithReagents._reagents_manager.remove(
        flowcell="B", reagent_name="temp"
    )
    BaseTestSequencerWithReagents._reagents_manager.remove(
        flowcell="B", reagent_name="test"
    )

    assert len(BaseTestSequencerWithReagents.flowcells["A"].reagents) == 2
    assert len(BaseTestSequencerWithReagents.flowcells["B"].reagents) == 2
    assert "temp" not in BaseTestSequencerWithReagents.flowcells["A"].reagents
    assert "temp" not in BaseTestSequencerWithReagents.flowcells["B"].reagents
    assert "test" not in BaseTestSequencerWithReagents.flowcells["B"].reagents


def test_remove_negntrl(BaseTestSequencerWithReagents):
    BaseTestSequencerWithReagents._reagents_manager.remove(
        flowcell="A", reagent_name="test"
    )
    assert len(BaseTestSequencerWithReagents.flowcells["A"].reagents) == 3
