import pytest
import asyncio


async def check_fc_queue(sequencer, only_check_filled=False, timeout=None):
    """Check to see if queue gets filled and then emptied."""
    try:
        flowcells = sequencer.enabled_flowcells
        # Check tasks added to queue
        for fc in flowcells:
            assert len(fc._queue_dict) >= 1

        if only_check_filled:
            return True

        # Wait for tasks to finish
        _ = []
        for fc in flowcells:
            _.append(fc._queue.join())

        await asyncio.wait_for(asyncio.gather(*_), timeout)

        # Check tasks cleared
        for fc in flowcells:
            assert len(fc._queue_dict) == 0

        return True

    except AssertionError:
        return False


@pytest.mark.asyncio
async def test_temperature(BaseTestSequencer):
    for t in [25, 37, 50]:
        BaseTestSequencer.temperature(temperature=t)
        for fc in BaseTestSequencer.enabled_flowcells:
            await fc.TemperatureController.wait_for_temperature(
                t, timeout=1, interval=0.01
            )


@pytest.mark.asyncio
async def test_pump(BaseTestSequencer):
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


@pytest.mark.asyncio
async def test_wait(BaseTestSequencer):
    pass


@pytest.mark.asyncio
async def test_image(BaseTestSequencer):
    pass


@pytest.mark.asyncio
async def test_focus(BaseTestSequencer):
    pass


@pytest.mark.asyncio
async def test_expose(BaseTestSequencer):
    pass
