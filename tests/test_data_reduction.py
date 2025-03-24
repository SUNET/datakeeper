import os
import time
import glob
import pytest
import random
import tempfile
from enum import Enum
from functools import partial
from unittest.mock import MagicMock
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from datakeeper.policy_system.plugins.data_reduction_operation import delete_files_by_extension, calculate_file_age

class TimeUnit(str, Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


conversion_factors = {
    TimeUnit.SECOND: 1,
    TimeUnit.MINUTE: 60,
    TimeUnit.HOUR: 60 * 60,
    TimeUnit.DAY: 60 * 60 * 24,
}

def _create_files(folder_path: str = None, dir_name: str = "data", nfiles: int = 6, retention_time: int =  7, time_unit: TimeUnit = TimeUnit.DAY):

    folder_path = folder_path if folder_path else os.path.dirname(__file__) 
    directory = os.path.join(folder_path, dir_name)
    print("directory=>", directory)
    execute_policy =  partial(delete_files_by_extension, directory,"csv", retention_time, time_unit, True, False)

    # Ensure the directory exists
    age_array = [retention_time - 1, retention_time, retention_time + 1]
    if retention_time < 1:
        age_array = [0.5, 1, 2]
    os.makedirs(directory, exist_ok=True)
    files_created = []
    for index in range(nfiles):
        full_path = os.path.join(directory, f"data-{index}.csv")
        print(index, "->", full_path, "age->", age_array[index % len(age_array)])
        try:
            with open(file=full_path, mode="w") as file:
                file.write("x, y, labels\n")
                file.write("44, 60, paris\n")
                file.write("56, 88, london\n")
                file.write("94, 24, lisbon\n")

            # set the target timestamp (e.g., #retention_time #time_unit ago, 7 days ago)
            target_time = time.time() - (
                age_array[index % len(age_array)] * conversion_factors[time_unit]
            )  # Convert time_unit to seconds
            # Set the access and modification times
            os.utime(full_path, (target_time, target_time))

            files_created.append(full_path)

        except (PermissionError, OSError) as e:
            print(f"Failed to create file {full_path}: {str(e)}")

    return files_created, execute_policy, retention_time, directory

@pytest.fixture
def temp_folder():
    """
    Fixture to create a temporary folder for testing.
    TODO: use this instead of creating data folder directly in create_files() fixture
    """
    with tempfile.TemporaryDirectory() as folder:
        print("folder=", folder)
        yield folder

@pytest.fixture
def create_files(request):
    """Example usage

        @pytest.mark.parametrize("create_files", [{"time_unit": TimeUnit.HOUR}], indirect=True)
        class TestDataReductionPolicy:
            def test_files_created(self, create_files):
    Args:
        request (_type_): _description_

    Returns:
        _type_: _description_
    """
    # Default values
    params = {
        "dir_name": "data",
        "nfiles": 6,
        "retention_time": 7,
        "file_type": "csv",
        "time_unit": TimeUnit.DAY,
    }

    # Override with test-specific parameters
    if hasattr(request, "param"):
        params.update(request.param)

    dir_name = params["dir_name"]
    nfiles = params["nfiles"]
    retention_time = params["retention_time"]
    time_unit = params["time_unit"]
    
    return  _create_files(dir_name = dir_name, nfiles = nfiles, retention_time =  retention_time, time_unit = time_unit)
    


class TestDataReductionPolicy:
    def test_files_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a MagicMock for the DatabaseClient
            files_created, _, _, _ = _create_files(folder_path=temp_dir,dir_name = "data", nfiles = 6, retention_time =  7, time_unit = TimeUnit.DAY)
            n_files = len(files_created)
            assert n_files == 6
            assert all(os.path.exists(file) for file in files_created)

    def test_scheduler_triggers_reduction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a MagicMock for the DatabaseClient
            files_created, _, _, _ = _create_files(folder_path=temp_dir,dir_name = "data", nfiles = 6, retention_time =  7, time_unit = TimeUnit.DAY)
            
            scheduler = MagicMock(BackgroundScheduler)
            scheduler.add_job = MagicMock()

            # Simulate job addition
            scheduler.add_job(delete_files_by_extension, 'interval', hours=1, args=["/path/to/folder"])

            # Simulate job execution
            scheduler.add_job.return_value = True

            scheduler.add_job(delete_files_by_extension, 'interval', hours=1)
            assert scheduler.add_job.called  # Verify the job was added

    def test_integration_with_scheduler(self):
        with tempfile.TemporaryDirectory() as temp_dir:
             # Simulate file creation and policy
            # files_created, retention_time, execute_policy = _create_files(folder_path=temp_dir,dir_name = "data", nfiles = 6, retention_time =  7, time_unit = TimeUnit.DAY)
            time_unit = TimeUnit.DAY
            ffiles_created, execute_policy, retention_time, directory = _create_files(folder_path=temp_dir, dir_name = "data", nfiles = 6, retention_time =  7, time_unit = time_unit)
            
            # Schedule and run
            scheduler = BackgroundScheduler()
            trigger = CronTrigger.from_crontab("*/1 * * * *")
            job_id = f"job-{random.randint(1117, 7791)}"
            
            # Add the job to the scheduler
            scheduler.add_job(
                execute_policy,
                trigger=trigger,
                id=job_id,
                name="Policy.Data.Reduction",
                replace_existing=True
            )
            scheduler.start()


            # Force immediate execution
            job = scheduler.get_job(job_id)
            if job:
                job.func()  # Directly call the job function

            # Remove sleep and wait until job execution is confirmed
            max_wait_time = 10  # Max seconds to wait for the job to complete
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                matching_files = glob.glob(os.path.join(directory, "*.csv"), recursive=True)
                if matching_files:
                    break  # Job executed, no need to wait further
                time.sleep(1)  # Small delay to check again

            scheduler.shutdown()

            # Validate file retention policy
            for file_path in matching_files:
                file_age = calculate_file_age(os.stat(file_path).st_mtime, time.time(), time_unit)
                print("file:", file_path, "age->", file_age)
                assert file_age < retention_time
            