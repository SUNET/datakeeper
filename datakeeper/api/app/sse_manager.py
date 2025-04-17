import json
import asyncio
import threading
import queue

# Thread-safe queue for communication between threads
thread_safe_queue = queue.Queue()

# Async queues for the event loops
job_event_queue = None
data_event_queue = None
main_event_loop = None  # store main event loop safely

def get_job_event_queue():
    global job_event_queue
    if job_event_queue is None:
        job_event_queue = asyncio.Queue()
    return job_event_queue

def set_main_event_loop(loop):
    global main_event_loop
    main_event_loop = loop
    # Start a background task to process the thread-safe queue
    asyncio.create_task(process_thread_queue())

def get_main_event_loop():
    if main_event_loop is None:
        raise RuntimeError("Main event loop is not set.")
    return main_event_loop

# Thread-safe method to enqueue events from any thread
def enqueue_job_update(data):
    thread_safe_queue.put(data)

# Async task that runs in the main event loop and processes the thread-safe queue
async def process_thread_queue():
    while True:
        try:
            # Use a short timeout to avoid blocking the event loop
            while not thread_safe_queue.empty():
                data = thread_safe_queue.get_nowait()
                await get_job_event_queue().put(data)
                thread_safe_queue.task_done()
        except queue.Empty:
            pass
        
        # Give control back to the event loop
        await asyncio.sleep(0.1)

async def data_stream():
    while True:
        data = await data_event_queue.get()
        yield f"event: data_update\ndata: [Data={data}]\n\n"

async def event_stream():
    while True:
        data = await job_event_queue.get()
        yield f"event: job_update\ndata: {json.dumps(data)}\n\n"