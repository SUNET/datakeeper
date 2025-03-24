import os
import glob
import time
from enum import Enum
from typing import List
from typing import Dict, Any
from datetime import datetime
from datakeeper.database.db import Database
from datakeeper.policy_system.plugin_registry import Operation, PluginRegistry


class TimeUnit(str, Enum):
    """
    Enum representing time units for file age filtering.
    time_hour = TimeUnit("hour")
    print("Hour=", time_hour, "str(h)=", str(time_hour))
    """

    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


def calculate_file_age(
    file_timestamp: float, current_time: float, unit: TimeUnit
) -> float:
    """
    Calculate file age in the specified time unit.

    Args:
        file_timestamp: File modification timestamp in seconds
        current_time: Current time in seconds
        unit: Time unit for the result

    Returns:
        File age in the specified unit
    """
    age_in_seconds = current_time - file_timestamp

    conversion_factors = {
        TimeUnit.SECOND: 1,
        TimeUnit.MINUTE: 60,
        TimeUnit.HOUR: 60 * 60,
        TimeUnit.DAY: 60 * 60 * 24,
    }

    return age_in_seconds / conversion_factors[unit]


def delete_files_by_extension(
    directory: str,
    extension: str,
    retention_time: int,
    time_unit: TimeUnit = TimeUnit.DAY,
    recursive: bool = False,
    dry_run: bool = False,
    logger=None,
) -> List[str]:
    """
    Delete all files with the specified extension in the given directory.

    Args:
        directory: Directory path to search for files
        extension: File extension to match (without the dot)
        recursive: Whether to search subdirectories
        dry_run: If True, only list files that would be deleted without deleting them
        retention_time: Only delete files older than this value
        time_unit: Unit for the retention_time parameter (second, minute, hour, day)
        logger: Logger object for logging (if None, print will be used)

    Returns:
        List of deleted file paths

    Raises:
        FileNotFoundError: If the directory doesn't exist
        PermissionError: If there are permission issues
        ValueError: If invalid parameters are provided
    """
    log = logger.info if logger else print
    log_debug = logger.debug if logger else print
    log_error = logger.error if logger else print

    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    # Normalize extension format
    if extension.startswith("."):
        extension = extension[1:]

    # Build the pattern for glob
    pattern = f"**/*.{extension}" if recursive else f"*.{extension}"

    # Get current time for age comparison
    current_time = time.time()
    deleted_files = []

    try:
        # Use glob with recursive flag for directory traversal if needed
        matching_files = glob.glob(
            os.path.join(directory, pattern), recursive=recursive
        )
        log(f"Found {len(matching_files)} files with extension .{extension}")

        for file_path in matching_files:
            try:
                file_stat = os.stat(file_path)
                file_age = calculate_file_age(
                    file_stat.st_mtime, current_time, time_unit
                )

                if file_age < retention_time:
                    log_debug(
                        f"Skipping {file_path} as it's not old enough "
                        f"(age: {file_age:.2f} {time_unit}s, threshold: {retention_time} {time_unit}s)"
                    )
                    continue

                if dry_run:
                    log(
                        f"Would delete: {file_path}, age: {file_age:.2f} {time_unit}s old"
                    )
                else:
                    os.remove(file_path)
                    log(f"Deleted: {file_path}, age: {file_age:.2f} {time_unit}s old")

                deleted_files.append(file_path)
            except (PermissionError, OSError) as e:
                log_error(f"Failed to delete {file_path}: {str(e)}")

    except Exception as e:
        log_error(f"Error during file deletion process: {str(e)}")
        raise

    return deleted_files


@PluginRegistry.register_operation
class DataReductionOperation(Operation):
    """Operation that reduces data according to specified parameters."""

    def __init__(self, log_file: str = "data_reduction.log"):
        super().__init__(log_file)

    def execute(self, context: Dict[str, Any]) -> Any:
        database: Database = context["database"]
        policy_id = context["policy_id"]
        data_type = context.get("data_type", ["csv"])
        file_paths = context.get("file_paths", [])
        time_unit = context.get("time_unit", None)
        retention_time = context.get("retention_time", None)
        try:
            self.log_info(f"DataReductionOperation->data_type:{data_type}")
            self.log_info(f"DataReductionOperation->file_paths:{file_paths}")
            self.log_info(f"DataReductionOperation->time_unit:{time_unit}")
            self.log_info(f"DataReductionOperation->retention_time:{retention_time}")
            self.log_info(f"DataReductionOperation->policy_id:{policy_id}")
            self.log_info(f"DataReductionOperation->database:{database}")
            self.log_info(f"context:{context}")
            database.update_schedule(policy_id, {"status": "running"})
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            for dir in file_paths:
                for file_type in data_type:
                    delete_files_by_extension(
                        directory=dir,
                        extension=file_type,
                        retention_time=2,
                        time_unit=TimeUnit(time_unit),
                        recursive=True,
                        dry_run=False,
                        logger=self.logger,
                    )

            self.log_info(
                f"[{timestamp}] Executing data reduction on {context.get('file_paths', 'unknown file')}"
            )
            database.update_schedule(policy_id, {"status": "success"})
            return context
        except Exception as err:
            self.log_error(
                f"Error Executing data reduction on {context.get('file_paths', 'unknown file')}: {err}"
            )
            database.update_schedule(
                policy_id, {"status": "failed", "last_error": str(err)}
            )
