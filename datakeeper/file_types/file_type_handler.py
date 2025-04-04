import h5py
import pandas as pd
from typing import Any
from pathlib import Path
from abc import ABC, abstractmethod


class FileTypeHandler(ABC):
    """Abstract base class for handling different file types."""

    def __init__(self, file_type: str, file_path: str):
        self.file_type = file_type
        self.file_path = Path(file_path)

    @abstractmethod
    def open(self, mode='r'):
        """Opens the file in the given mode."""
        pass

    @abstractmethod
    def close(self, file_obj):
        """Closes the file object."""
        pass

    @abstractmethod
    def save(self, data: Any):
        """Saves data to a file."""
        pass

    @abstractmethod
    def load(self) -> Any:
        """Loads data from a file."""
        pass

    @abstractmethod
    def get_metadata(self, file_obj) -> dict:
        """Retrieves metadata from the file."""
        pass


class HDF5Handler(FileTypeHandler):
    """Handler for HDF5 files."""

    def __init__(self, file_path: str):
        super().__init__('hdf5', file_path)

    def open(self, mode='r'):
        """Opens an HDF5 file."""
        return h5py.File(self.file_path, mode)

    def close(self, file_obj):
        """Closes an HDF5 file."""
        file_obj.close()

    def save(self, data: pd.DataFrame):
        """Saves a Pandas DataFrame to an HDF5 file."""
        data.to_hdf(self.file_path, key="df", mode="w")
        print(f"Saved HDF5 file: {self.file_path}")

    def load(self) -> pd.DataFrame:
        """Loads data from an HDF5 file into a Pandas DataFrame."""
        return pd.read_hdf(self.file_path)

    def get_metadata(self, file_obj) -> dict:
        """Gets metadata from an HDF5 file."""
        return {
            'datasets': list(file_obj.keys()),
            'attributes': dict(file_obj.attrs.items())
        }


class CSVHandler(FileTypeHandler):
    """Handler for CSV files."""

    def __init__(self, file_path: str):
        super().__init__('csv', file_path)

    def open(self, mode='r'):
        """Opens a CSV file."""
        return open(self.file_path, mode)

    def close(self, file_obj):
        """Closes a CSV file."""
        file_obj.close()

    def save(self, data: pd.DataFrame, **kwargs):
        """Saves a Pandas DataFrame to a CSV file."""
        data.to_csv(self.file_path, index=False, **kwargs)
        print(f"Saved CSV file: {self.file_path}")

    def load(self, **kwargs) -> pd.DataFrame:
        """Loads a CSV file into a Pandas DataFrame."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File {self.file_path} not found")

        if self.file_path.suffix.lower() != '.csv':
            raise ValueError(f"Unsupported file format: {self.file_path.suffix}")

        return pd.read_csv(self.file_path, **kwargs)

    def get_metadata(self, file_obj) -> dict:
        """Metadata for CSV is limited, returning file size."""
        return {
            'file_size': self.file_path.stat().st_size
        }
