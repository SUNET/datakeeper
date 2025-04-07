import os
import uuid
import time
import h5py
import random
import string
from multiprocessing import Process, JoinableQueue
import numpy as np
import pandas as pd
from pathlib import Path
from functools import partial
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from datakeeper.mixins.logger import LoggerMixin
from datakeeper.policy_system.plugins.data_reduction_operation import (
    TimeUnit
)


def rec_pop(data, acc={}):
    titles = list(data)
    for t in titles:
        curr_data = data[t]
        if isinstance(curr_data, h5py._hl.dataset.Dataset):
            acc[t] = curr_data[()]
        elif isinstance(curr_data, h5py._hl.group.Group):
            acc[t] = rec_pop(curr_data, {})
        else:
            print("Unkown type:::", type(curr_data))
            return acc
    return acc

class DataGenerator(LoggerMixin):
    """
    A production-ready class for saving various data types to disk in multiple formats.
    
    Supported formats:
    - CSV (.csv)
    - HDF5 (.h5)
    
    This class can be extended to support additional file formats.
    """
    
    # Dictionary of supported file formats and their corresponding save methods
    SUPPORTED_FORMATS = {
        'csv': '_save_csv',
        'hdf5': '_save_hdf5',
        'h5': '_save_hdf5'
    }
    
    def __init__(self, base_directory: str = "./data", random_age: bool = True, number_of_files: int = 10,  create_dir: bool = True,  log_file: str="data_generator.log"):
        """
        Initialize the DataGenerator.
        
        Args:
            base_directory (str): Base directory to store data files
            create_dir (bool): Whether to create the directory if it doesn't exist
        """
        # Set up logging
        super().__init__(log_file)
        
        self.base_directory = Path(base_directory)
        self.random_age = random_age
        self.number_of_files = number_of_files
        self.add_timestamp = not random_age 
        self.conversion_factors = {
            TimeUnit.SECOND: 1,
            TimeUnit.MINUTE: 60,
            TimeUnit.HOUR: 60 * 60,
            TimeUnit.DAY: 60 * 60 * 24,
        }

        if create_dir and not self.base_directory.exists():
            self.base_directory.mkdir(parents=True, exist_ok=True)
    
    def generate_random_dataframe(
        self,
        rows: int = 10,
        cols: int = 5,
        column_types: list = None,
        seed: int = None
    ) -> pd.DataFrame:
        """
        Generate a random DataFrame with specified number of rows and columns.
        
        Parameters:
        - rows (int): Number of rows in the DataFrame.
        - cols (int): Number of columns in the DataFrame.
        - column_types (list): List specifying data types for each column. Options: 'int', 'float', 'str', 'bool', 'datetime'.
        - seed (int, optional): Random seed for reproducibility.
        
        Returns:
        - pd.DataFrame: A DataFrame with randomly generated data.
        
        # Example usage:
        df = generate_random_dataframe(rows=10, cols=4, column_types=['int', 'float', 'str', 'datetime'], seed=42)
        print(df)
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
        
        if column_types is None:
            column_types = random.choices(['int', 'float', 'str', 'bool', 'datetime'], k=cols)
        elif len(column_types) != cols:
            raise ValueError("Length of column_types must match cols")
        
        data = {}
        for i, col_type in enumerate(column_types):
            col_name = f"col_{i}"
            
            if col_type == 'int':
                data[col_name] = np.random.randint(0, 1000, size=rows)
            elif col_type == 'float':
                data[col_name] = np.random.uniform(0, 1000, size=rows)
            elif col_type == 'str':
                data[col_name] = [''.join(random.choices(string.ascii_letters, k=10)) for _ in range(rows)]
            elif col_type == 'bool':
                data[col_name] = np.random.choice([True, False], size=rows)
            elif col_type == 'datetime':
                start_date = datetime(2000, 1, 1)
                data[col_name] = [start_date + timedelta(days=random.randint(0, 7300)) for _ in range(rows)]
            else:
                raise ValueError(f"Unsupported column type: {col_type}")
        
        return pd.DataFrame(data) 
        
    def generate(self,
             subdirectory: Optional[str] = None,
             format: Optional[str] = "csv",
             additional_params: Dict[str, Any] = None) -> str:
        """
        Save data to a file in the specified format.
        
        Args:
            data: Data to save (DataFrame, dict, list, or numpy array)
            filename: Name for the saved file (without extension)
            subdirectory: Optional subdirectory within base_directory
            format: File format (csv, excel, hdf5)
            additional_params: Additional parameters for the save method
            timestamp: Whether to append a timestamp to the filename
            
        Returns:
            str: Path to the saved file
        """

        # Default parameters
        format = format.lower()
        additional_params = additional_params or {}
        
        #  filename 
        filename = f"data_{uuid.uuid4().hex[:8]}"
            
        # Add timestamp if requested
        if self.add_timestamp:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp_str}"
        
        # Check if format is supported
        if format not in self.SUPPORTED_FORMATS:
            supported_formats = list(self.SUPPORTED_FORMATS.keys())
            self.logger.error(f"Format '{format}' is not supported. Choose from: {supported_formats}")
            raise ValueError(f"Format '{format}' is not supported. Choose from: {supported_formats}")
        
        # Determine file path
        save_dir = self.base_directory
        if subdirectory:
            save_dir = save_dir / subdirectory
            save_dir.mkdir(parents=True, exist_ok=True)
        
        # Call the appropriate save method
        save_method_name = self.SUPPORTED_FORMATS[format]
        save_method = getattr(self, save_method_name)
        queue = JoinableQueue()
        PROCESSES_POOL_SIZE = min(self.number_of_files, 10)
        try:
            for index in range(self.number_of_files):
                file_path = save_dir / f"{filename}-{index+1}.{format}"  
                queue.put(save_dir / f"{filename}-{index+1}.{format}"  )

            processes = [
                Process(target=partial(save_method, **additional_params), args=(queue,), daemon=True)
                for _ in range(PROCESSES_POOL_SIZE)
            ]

            for p in processes:
                p.start()
            queue.join()
            self.logger.info(f"Successfully saved data to {self.base_directory}")
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Error saving data to {self.base_directory}: {e}")
            raise
    
    
    def set_random_age(self, file_path):
        if self.random_age:
            time_unit = random.choice(list(TimeUnit))
            target_time = time.time() - (random.randint(15,60) * self.conversion_factors[time_unit])
            os.utime(file_path, (target_time, target_time))
            
            
    def _save_csv(self, queue: JoinableQueue, **kwargs) -> None:
        while True:
            file_path = queue.get()
            try:
                data = self.generate_random_dataframe(rows=16, cols=6)
                """Save data to CSV file."""
                # Set sensible defaults if not provided
                params = {
                    'index': kwargs.get('index', False),
                    'sep': kwargs.get('sep', ','),
                    'encoding': kwargs.get('encoding', 'utf-8')
                }
                data.to_csv(file_path, **params)
                self.set_random_age(file_path)
            except Exception as e:
                print(f"Error creating file {file_path}: {e}")
            finally:
                queue.task_done()
    
    
    
    def _save_hdf5(self, queue: JoinableQueue, **kwargs) -> None:
        """Save data to HDF5 file."""
        while True:
            file_path = queue.get()
            try:
                # Create synthetic data for the main dataset
                data = np.random.randint(-150, 150, size=(10417, 16000), dtype=np.int16)

                # Create the HDF5 file
                with h5py.File(file_path, "w") as f:
                    # Create the datasets
                    f.create_dataset("data", data=data)
                    f.create_dataset("fileGenerator", data=np.bytes_("DASControl"))
                    f.create_dataset("fileGeneratorSvnRev", data=np.uint32(2403011412))
                    f.create_dataset("fileVersion", data=np.int32(8))

                    # Create the groups
                    f.create_group("acqSpec")
                    f.create_group("cableSpec")
                    f.create_group("demodSpec")
                    f.create_group("header")
                    f.create_group("instrumentOptions")
                    f.create_group("monitoring")
                    f.create_group("processingChain")
                    f.create_group("sweepSpec")
                    f.create_group("timing")
                    f.create_group("versions")
                    self.set_random_age(file_path)

            except Exception as e:
                print(f"Error creating file {file_path}: {e}")
            finally:
                queue.task_done()
                
    def register_format(self, format_name: str, save_method: callable) -> None:
        """
        Register a new file format and its corresponding save method.
        
        Args:
            format_name (str): Name of the format (extension)
            save_method (callable): Method that saves data in this format
        """
        format_name = format_name.lower()
        method_name = f"_save_{format_name}"
        
        # Add the method to the class instance
        setattr(self, method_name, save_method)
        
        # Register the format in SUPPORTED_FORMATS
        self.SUPPORTED_FORMATS[format_name] = method_name
        self.logger.info(f"Registered new format: {format_name}")

    def load(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        Load data from a file.
        
        Args:
            file_path (str): Path to the file to load
            kwargs: Additional parameters for the load method
            
        Returns:
            pd.DataFrame: Loaded data
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
            
        # Determine format from file extension
        extension = file_path.suffix.lower()[1:]  # Remove the leading dot
        
        if extension == 'csv':
            return pd.read_csv(file_path, **kwargs)
        elif extension in ['xlsx', 'xls']:
            return pd.read_excel(file_path, **kwargs)
        elif extension in ['h5', 'hdf5']:
            key = kwargs.pop('key', 'data')
            return pd.read_hdf(file_path, key=key, **kwargs)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
        
        
        
if __name__ == "__main__":
    
    base_dir = "/home/benedith/Desktop/tests/datasentry/datakeeper/datakeeper/data_ok"
    
    data_generator = DataGenerator(base_directory=base_dir, random_age=True, number_of_files=5, create_dir=True)
    data_generator.generate(format="hdf5")
    data_generator.generate(subdirectory="daily_reports", format="hdf5")
    # path = data_generator.save(format="excel",  additional_params={"sheet_name": "Results"})
    