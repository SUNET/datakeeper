import os
import glob
import h5py
import numpy as np
from typing import List
from typing import Dict, Any
from datetime import datetime
from datakeeper.database.db import Database
from datakeeper.policy_system.plugin_registry import Operation, PluginRegistry


def downsample_dataset(dataset, temporal_factor=None, spatial_factor=None, method=None):
    """
    Downsample an HDF5 dataset (or numpy array) in temporal and/or spatial dimensions.
    
    Parameters:
    -----------
    dataset : h5py.Dataset or numpy.ndarray
        The dataset to downsample. Expected shape: (time_points, channels, ...)
    temporal_factor : int or None
        Factor by which to reduce the temporal dimension. If None, no temporal downsampling.
    spatial_factor : int or None
        Factor by which to reduce the spatial (channel) dimension. If None, no spatial downsampling.
    method : str
        Method for downsampling: 'mean', 'sum', 'max', 'min', 'None'.
        'None' simply takes the first element of each group without aggregation.
        Default is 'mean'.
    
    Returns:
    --------
    numpy.ndarray
        Downsampled array
    """
    
    # Convert to numpy array if it's an HDF5 dataset
    if isinstance(dataset, h5py.Dataset):
        data = dataset[:]
    else:
        data = dataset
    
    # Validate input parameters
    if not (temporal_factor or spatial_factor):
        return data
    
    # Implement temporal downsampling
    if temporal_factor:
        # Calculate new time dimension
        time_points = data.shape[0]
        new_time_points = time_points // temporal_factor
        
        # Truncate data to be evenly divisible by temporal_factor
        truncated_length = new_time_points * temporal_factor
        data_trunc = data[:truncated_length]
        
        # Reshape to group time points for reduction
        reshaped = data_trunc.reshape((new_time_points, temporal_factor) + data_trunc.shape[1:])
        
        # Apply the selected reduction method along axis 1 (temporal groups)
        if method is None:
            # Take the first element of each group without any operation
            data = reshaped[:, 0]
        elif method == 'mean':
            data = np.mean(reshaped, axis=1)
        elif method == 'sum':
            data = np.sum(reshaped, axis=1)
        elif method == 'max':
            data = np.max(reshaped, axis=1)
        elif method == 'min':
            data = np.min(reshaped, axis=1)
        else:
            raise ValueError(f"Method '{method}' not supported. Use 'mean', 'sum', 'max', 'min', or 'None'.")
    
    # Implement spatial (channel) downsampling
    if spatial_factor:
        # Calculate new channel dimension
        channels = data.shape[1]
        new_channels = channels // spatial_factor
        
        # Truncate channels to be evenly divisible by spatial_factor
        truncated_channels = new_channels * spatial_factor
        data_trunc = data[:, :truncated_channels]
        
        # Reshape to group channels for reduction
        shape = data_trunc.shape
        reshaped = data_trunc.reshape(shape[0], new_channels, spatial_factor, *shape[2:])
        
        # Apply the selected reduction method along axis 2 (channel groups)
        if method is None:
            # Take the first element of each group without any operation
            data = reshaped[:, :, 0]
        elif method == 'mean':
            data = np.mean(reshaped, axis=2)
        elif method == 'sum':
            data = np.sum(reshaped, axis=2)
        elif method == 'max':
            data = np.max(reshaped, axis=2)
        elif method == 'min':
            data = np.min(reshaped, axis=2)
    
    return data


def copy_hdf5(source_file, target_file, exclude_paths=None, logger=None):
    log = logger.info if logger else print
    if exclude_paths is None:
        exclude_paths = []
    
    # Normalize paths for easier comparison
    exclude_paths = [path.rstrip('/') for path in exclude_paths]
    
    try:
        with h5py.File(source_file, 'r') as source:
            with h5py.File(target_file, 'w') as target:
                # Define a recursive copy function to handle nested groups
                def _copy_recursively(name, obj):
                    # Check if current path should be excluded
                    if any(name == path or name.startswith(path + '/') for path in exclude_paths):
                        log(f"Skipping excluded path: {name}")
                        return
                    
                    # Handle groups (directories)
                    if isinstance(obj, h5py.Group):
                        if name:  # Skip root group
                            # Create group in target file if it doesn't exist
                            if name not in target:
                                target.create_group(name)
                            
                            # Copy attributes
                            for attr_name, attr_value in obj.attrs.items():
                                target[name].attrs[attr_name] = attr_value
                    
                    # Handle datasets
                    elif isinstance(obj, h5py.Dataset):
                        # Create the parent groups if they don't exist
                        parent_path = os.path.dirname(name)
                        if parent_path and parent_path not in target:
                            target.create_group(parent_path)
                        
                        # Copy the dataset
                        data = obj[()]
                        dataset = target.create_dataset(name, data=data, dtype=obj.dtype, 
                                                       compression=obj.compression, 
                                                       compression_opts=obj.compression_opts)
                        
                        # Copy attributes
                        for attr_name, attr_value in obj.attrs.items():
                            dataset.attrs[attr_name] = attr_value
                
                # Start the recursive copy process
                source.visititems(_copy_recursively)
        
        return True
    
    except Exception as e:
        log(f"Error copying HDF5 file: {e}")
        return False


def downsample_hdf5_file(data_files,
                        extension,
                        dataset_paths = ["data"], 
                        temporal_factor=None, 
                        spatial_factor=None, 
                        method='mean', 
                        make_copy=True,
                        logger=None,):

    log = logger.info if logger else print
    extension = clean_extension(extension)
    log(f"data_files->{data_files}")
    log(f"directory->{dir}")
    file_access_method = 'a' if make_copy else 'w'
    for data_file in data_files:
        curr_dir, filename = data_file.rsplit('/', 1)
        new_data_file = os.path.join(curr_dir, f"{filename.rsplit('.', 1)[0]}_temp.{extension}")
        log(f"data_file->{data_file, new_data_file}")
        if make_copy:
            copy_hdf5(data_file, new_data_file, exclude_paths=dataset_paths, logger=logger)

        with h5py.File(data_file, 'r') as fin, h5py.File(new_data_file, file_access_method) as fout:
            for path in dataset_paths:
                data = fin[path]
                
                # TODO: call downsamplign
                downsampled = downsample_dataset(data, temporal_factor = temporal_factor)
                
                
                # Create output dataset (create parent groups if needed)
                group_path = path.rsplit('/', 1)[0] if '/' in path else '/'
                if group_path != '/' and group_path not in fout:
                    fout.create_group(group_path)
                
                ds = fout.create_dataset(path, data=downsampled, compression='gzip')
                
                # Copy attributes from original dataset
                for key, value in data.attrs.items():
                    ds.attrs[key] = value
                
                # Add downsampling information to attributes
                ds.attrs['downsampled_from_original'] = True
                if temporal_factor:
                    ds.attrs['temporal_downsampling_factor'] = temporal_factor
                if spatial_factor:
                    ds.attrs['spatial_downsampling_factor'] = spatial_factor
                ds.attrs['downsampling_method'] = method


        # Replace the original file with the downsampled version
        if os.path.exists(data_file):
            os.remove(data_file)
        os.rename(new_data_file, data_file)


def clean_extension(extension):
    # Normalize extension format
    if extension.startswith("."):
        return  extension[1:]
    return extension 


def get_directories_files(
    directory: str,
    extension: str,
    recursive: bool = False,
    logger=None,
) -> List[str]:

    log = logger.info if logger else print

    # Normalize extension format
    extension = clean_extension(extension)

    # Build the pattern for glob
    pattern = f"**/*.{extension}" if recursive else f"*.{extension}"

    matching_files = glob.glob(
        os.path.join(directory, pattern), recursive=recursive
    )
    log(f"Found {len(matching_files)} files with extension .{extension}")
    return matching_files


@PluginRegistry.register_operation
class DataDownSamplingOperation(Operation):
    """Operation that reduces data according to specified parameters."""

    def __init__(self, log_file: str = "data_downsampling.log"):
        super().__init__(log_file)

    def execute(self, context: Dict[str, Any]) -> Any:

        database: Database = context.get("database")
        if not isinstance(database, Database):
            raise TypeError("'database' must be an instance of Database.")
        policy_id = context.get("policy_id")
        data_type = context.get("data_type", ["csv"])
        file_paths = context.get("file_paths", [])
        methods = context.get("methods", [])
        try:
            self.log_info(f"DataReductionOperation->policy_id:{policy_id}")
            self.log_info(f"DataReductionOperation->database:{database}")
            self.log_info(f"context:{context}")
            self.log_info(f"methods:{methods}")
            database.update_schedule(policy_id, {"status": "running"})
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            for dir in file_paths:
                for file_type in data_type:
                    self.log_info(f"dir={dir}, file_type={file_type}")
                    data_files = get_directories_files(directory=dir, extension=file_type,recursive=True,logger=self.logger)
                    for index, method in enumerate(methods):
                        self.log_info(f"index.{index} -> methods:{method}")
                        self.log_info(f"{method['dimension']}")
                        self.log_info(f"{method['algorithm']}")
                        self.log_info(f"{method['factor']}")
                        self.log_info(f"{method['dataset']} --> {type(method['dataset'])}")
                        if method['dimension'] == "temporal":
                            downsample_hdf5_file(data_files,
                                                extension=file_type,
                                                dataset_paths = method['dataset'], 
                                                temporal_factor=method['factor'], 
                                                method=method['algorithm'], 
                                                make_copy=True,
                                                logger=self.logger,)
                        elif method['dimension'] == "spatial":
                            downsample_hdf5_file(data_files,
                                                extension=file_type,
                                                dataset_paths = method['dataset'], 
                                                spatial_factor=method['factor'], 
                                                method=method['algorithm'], 
                                                make_copy=True,
                                                logger=self.logger,)
            self.log_info(
                f"[{timestamp}] Executing downsampling on {context.get('file_paths', 'unknown file')}"
            )
            database.update_schedule(policy_id, {"status": "completed"})
            return context
        except Exception as err:
            self.log_error(
                f"Error Executing data reduction on {context.get('file_paths', 'unknown file')}: {err}"
            )
            database.update_schedule(
                policy_id, {"status": "failed", "last_error": str(err)}
            )
