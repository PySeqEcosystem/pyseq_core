import pytest
import asyncio


async def check_fc_queue(sequencer, only_check_filled=False, timeout=None):
    """Check to see if queue gets filled and then emptied."""
    try:
        flowcells = sequencer._get_fc_list()

        # Check tasks added to queue
        for fc in flowcells:
            assert len(sequencer.flowcells[fc]._queue_dict) >= 1

        if only_check_filled:
            return True

        # Wait for tasks to finish
        _ = []
        for fc in flowcells:
            _.append(sequencer.flowcells[fc]._queue.join())

        await asyncio.wait_for(asyncio.gather(*_), timeout)

        # Check tasks cleared
        for fc in flowcells:
            assert len(sequencer.flowcells[fc]._queue_dict) == 0

        return True

    except AssertionError:
        return False


@pytest.mark.asyncio
async def test_pump(BaseTestSequencer):
    print(BaseTestSequencer.flowcells["A"].Pump.config)
    BaseTestSequencer.pump(volume=100, flow_rate=4000, reagent=1)
    assert await check_fc_queue(BaseTestSequencer, timeout=1)


@pytest.mark.asyncio
async def test_hold(BaseTestSequencer):
    BaseTestSequencer.hold(duration=0.01)
    assert await check_fc_queue(BaseTestSequencer, timeout=1)


@pytest.mark.asyncio
async def test_pause(BaseTestSequencer):
    BaseTestSequencer.hold(duration=0.01)
    await asyncio.sleep(0.005 * 60)
    BaseTestSequencer.pause()
    BaseTestSequencer.hold(duration=0.005)
    assert await check_fc_queue(BaseTestSequencer, only_check_filled=True)
    await asyncio.sleep(0.01 * 60)
    BaseTestSequencer.start()
    assert await check_fc_queue(BaseTestSequencer, timeout=2)
