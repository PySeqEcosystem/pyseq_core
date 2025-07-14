import pytest
import asyncio
import logging


async def wait_for_microscope_queue(microscope):
    while len(microscope._queue_dict) == 0:
        await asyncio.sleep(0.05)
    assert len(microscope._queue_dict) > 0, "No tasks added to microscope queue"
    microscope.start()
    await microscope._queue.join()


def check_for_errors_in_log(caplog):
    errors = []
    for record in caplog.get_records("call"):
        if record.levelno > logging.ERROR:
            print(record)
            errors.append(record)
    if len(errors) > 0:
        return False
    else:
        return True


async def check_fc_queue(
    sequencer, caplog, only_check_filled=False, timeout=None, check_microscope=False
):
    """Check to see if queue gets filled and then emptied."""
    flowcells = sequencer.enabled_flowcells

    try:
        # Check tasks added to queue
        for fc in flowcells:
            assert len(fc._queue_dict) >= 1, f"No tasks added to {fc.name} queue"

        if only_check_filled:
            assert check_for_errors_in_log(caplog), "Errors in log"
            return True

        # Wait for tasks to finish
        _ = []
        for fc in flowcells:
            _.append(fc._queue.join())
        if check_microscope:
            m = sequencer.microscope
            _.append(wait_for_microscope_queue(m))
        await asyncio.wait_for(asyncio.gather(*_), timeout)

        # Check tasks cleared
        for fc in flowcells:
            assert len(fc._queue_dict) == 0, f"Tasks not cleared from {fc.name} queue"
        if check_microscope:
            assert len(m._queue_dict) == 0, f"Tasks not cleared from {m.name} queue"

        assert check_for_errors_in_log(caplog), "Errors in log"

        return True

    except AssertionError as e:
        print(e)
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
async def test_pump(BaseTestSequencer, caplog):
    BaseTestSequencer.pump(volume=100, flow_rate=4000, reagent=1)
    assert await check_fc_queue(BaseTestSequencer, caplog, timeout=1)


@pytest.mark.asyncio
async def test_hold(BaseTestSequencer, caplog):
    BaseTestSequencer.hold(duration=0.01)
    assert await check_fc_queue(BaseTestSequencer, caplog, timeout=1)


@pytest.mark.asyncio
async def test_pause(BaseTestSequencer, caplog):
    BaseTestSequencer.hold(duration=0.01)
    await asyncio.sleep(0.005 * 60)
    BaseTestSequencer.pause()
    BaseTestSequencer.hold(duration=0.005)
    assert await check_fc_queue(BaseTestSequencer, caplog, only_check_filled=True)
    await asyncio.sleep(0.01 * 60)
    BaseTestSequencer.start()
    assert await check_fc_queue(BaseTestSequencer, caplog, timeout=2)


@pytest.mark.asyncio
async def test_wait(BaseTestSequencer):
    pass


@pytest.mark.asyncio
async def test_image(BaseTestSequencerROIs, caplog):
    caplog.set_level(logging.ERROR)
    BaseTestSequencerROIs.microscope.pause()
    BaseTestSequencerROIs.image()
    assert await check_fc_queue(BaseTestSequencerROIs, caplog, check_microscope=True)


@pytest.mark.asyncio
async def test_focus(BaseTestSequencerROIs, caplog):
    caplog.set_level(logging.ERROR)
    BaseTestSequencerROIs.microscope.pause()
    BaseTestSequencerROIs.focus()
    assert await check_fc_queue(BaseTestSequencerROIs, caplog, check_microscope=True)


@pytest.mark.asyncio
async def test_expose(BaseTestSequencerROIs, caplog):
    caplog.set_level(logging.ERROR)
    BaseTestSequencerROIs.microscope.pause()
    BaseTestSequencerROIs.expose()
    assert await check_fc_queue(BaseTestSequencerROIs, caplog, check_microscope=True)
