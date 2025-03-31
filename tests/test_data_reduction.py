import os
import time
import glob
import pytest
import random
import tempfile
from functools import partial
from unittest.mock import patch, MagicMock
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from datakeeper.policy_system.plugins.data_reduction_operation import (
    delete_files_by_extension, 
    calculate_file_age, 
    TimeUnit
)

class TestDataReductionPolicy:
    @pytest.fixture
    def create_test_files(self):
        """
        Fixture to create test files with controlled aging for consistent testing.
        
        Returns:
            tuple: Contains directory path, created files, and execute policy function
        """
        def _create_files(
            folder_path: str = None,
            dir_name: str = "data",
            file_count=6, 
            retention_time=7, 
            time_unit=TimeUnit.DAY, 
            file_extension='csv'
        ):
            folder_path = folder_path if folder_path else os.path.dirname(__file__) 
            directory = os.path.join(folder_path, dir_name)
            print("directory=>", directory)
            # Ensure the directory exists
            os.makedirs(directory, exist_ok=True)
            
            # Create files with varied ages
            age_array = [
                retention_time - 1,  # Just under retention
                retention_time,      # Exactly at retention
                retention_time + 1   # Just over retention
            ]
            
            if retention_time < 1:
                age_array = [0.5, 1, 2]
                
            files_created = []
            conversion_factors = {
                TimeUnit.SECOND: 1,
                TimeUnit.MINUTE: 60,
                TimeUnit.HOUR: 60 * 60,
                TimeUnit.DAY: 60 * 60 * 24,
            }
            
            for index in range(file_count):
                filename = f"data-{index}.{file_extension}"
                filepath = os.path.join(directory, filename)
                print(index, "->", filepath, "age->", age_array[index % len(age_array)])
                # Create file with sample content
                with open(filepath, 'w') as f:
                    f.write("x, y, labels\n")
                    f.write("44, 60, paris\n")
                
                # Set file age
                target_time = time.time() - (
                    age_array[index % len(age_array)] * conversion_factors[time_unit]
                )
                os.utime(filepath, (target_time, target_time))
                
                files_created.append(filepath)
            
            # Create partial function for file deletion policy
            execute_policy =  partial(delete_files_by_extension, directory,file_extension, retention_time, time_unit, True, False)
            
            return directory, files_created, execute_policy
        
        return _create_files

    def test_files_creation(self, create_test_files):
        """
        Test that files are correctly created with the specified parameters.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            directory, files_created, _ = create_test_files(
                temp_dir, "data", file_count=6, retention_time=7, time_unit=TimeUnit.DAY
            )
            
            assert len(files_created) == 6
            assert all(os.path.exists(file) for file in files_created)

    def test_file_deletion_policy(self, create_test_files):
        """
        Test that files older than retention time are deleted.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            directory, files_created, execute_policy = create_test_files(
                temp_dir,"data", file_count=6, retention_time=7, time_unit=TimeUnit.DAY
            )
            
            # Execute deletion policy
            execute_policy()
            
            # Check remaining files
            remaining_files = glob.glob(os.path.join(directory, "*.csv"))
            assert len(remaining_files) <= len(files_created)
            
            # Verify each remaining file is within retention time
            for file_path in remaining_files:
                file_age = calculate_file_age(
                    os.stat(file_path).st_mtime, 
                    time.time(), 
                    TimeUnit.DAY
                )
                assert file_age < 7, f"File {file_path} exceeds retention time"


    def test_integration_with_scheduler(self, create_test_files):
        """
        Test integration with APScheduler, mocking the scheduler to avoid actual scheduling.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup mock scheduler and policy
            retention_time = 6
            time_unit = TimeUnit.DAY
            

            directory, files_created, execute_policy = create_test_files(
                temp_dir,"datax", file_count=6, retention_time=retention_time, time_unit=time_unit
            )
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
                