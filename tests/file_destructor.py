import os
import time
import glob
from typing import List
from enum import Enum


class TimeUnit(str, Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


def calculate_file_age(
    file_timestamp: float, current_time: float, unit: TimeUnit
) -> float:
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
) -> List[str]:
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
        print(f"Found {len(matching_files)} files with extension .{extension}")

        for file_path in matching_files:
            try:
                file_stat = os.stat(file_path)
                file_age = calculate_file_age(
                    file_stat.st_mtime, current_time, time_unit
                )

                if file_age < retention_time:
                    print(
                        f"Skipping {file_path} as it's not old enough "
                        f"(age: {file_age:.2f} {time_unit}s, threshold: {retention_time} {time_unit}s)"
                    )
                    continue

                if dry_run:
                    print(
                        f"Would delete: {file_path}, age: {file_age:.2f} {time_unit}s old"
                    )
                else:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}, age: {file_age:.2f} {time_unit}s old")

                deleted_files.append(file_path)
            except (PermissionError, OSError) as e:
                print(f"Failed to delete {file_path}: {str(e)}")

    except Exception as e:
        print(f"Error during file deletion process: {str(e)}")
        raise

    return deleted_files


def main():
    current_dir = os.path.dirname(__file__)
    dir = os.path.join(current_dir, "data", "csv")
    while True:
        print("deleting files...")
        delete_files_by_extension(dir, "csv", 2, TimeUnit.MINUTE, True, dry_run=False)
        print("Sleeping 30sec")
        time.sleep(30)


if __name__ == "__main__":
    main()
