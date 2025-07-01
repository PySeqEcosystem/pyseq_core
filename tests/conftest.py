import pytest_asyncio

@pytest_asyncio.fixture
async def BaseTestSequencer():
    from sequencers import test_sequencer
    
    seq = test_sequencer.TestSequencer(name='Test')
    seq.start()
    # return  seq

    yield seq

    # Sequencer Teardown

    # Stop loops
    seq.flowcells['A']._loop_stop = True
    seq.flowcells['B']._loop_stop = True
    seq.microscope._loop_stop = True
    seq._loop_stop = True

    # Cancel worker
    seq.flowcells['A']._worker_task.cancel()
    seq.flowcells['B']._worker_task.cancel()
    seq.microscope._worker_task.cancel()
    seq._worker_task.cancel()

    await seq.flowcells['A']._worker_task
    await seq.flowcells['B']._worker_task
    await seq.microscope._worker_task
    await seq._worker_task