# Datakeeper

The **Datakeeper** program is designed to maintain data size at reasonable levels for systems like DAS (Distributed Acoustic Sensing) by enforcing various criteria, such as retention periods and other data reduction strategies.

## Data Retention Policy

The DAS server stores data in **HDF5 format** at **10-second intervals**, creating a new folder for each day.

### **Function – Automatic Deletion**

The DAS box includes built-in support for automatic data deletion:

- Data is automatically removed after **X days** (the retention period).
- The retention period is configurable and can be adjusted based on specific needs.

### **Data Reduction Policy**

The **Data Reduction Policy** defines strategies to manage and reduce the volume of stored data:

#### **Features:**

- **Automatic Deletion**:  
  Data older than **X days** is automatically deleted, with configurable deletion strategies.

- **Modify Region of Interest (ROI)**:  
  Allows selection of specific channels, e.g., **n[i]...n[j]**, from the HDF5 file. The selected region is saved into a new HDF5 file for further analysis.

- **Reduce Sampling Rate**:  
  - **Temporal Downsampling**: Reduce the data sampling rate in time, using techniques like averaging or summation.
  - **Spatial Downsampling**: Reduce the number of channels (space), again using aggregation methods like averaging or summation.

- **Remove Specific Time Segments**:  
  Retain only the data from defined time blocks, for example, between **12:05 – 14:30**, focusing on a specific region of interest.

- **Event-driven Storage**:  
  When an event occurs, data from relevant channels within a **±X km range** or **±X seconds** around the event is saved for later use.

- **Geofence-based Storage**:  
  When an **AIS (Automatic Identification System) signal** is detected within a defined geofenced area, data is retained to ensure critical information isn't lost.

---

## 🚀 Installation Guide


Please note that **Git** is required for all installation methods. Additionally, **DataKeeper** requires either:

- **Python 3.9**,  
- **GLIBC 2.33** or higher.

You can check your GLIBC version with the following command:

```bash
ldd --version
```


You can install **DataKeeper** using one of the following methods:

### **1. One-liner Script Installation**

#### Without Building the Binary

Use this method for a quick setup (downloads a prebuilt version):

```bash
curl -sSfL https://raw.githubusercontent.com/SUNET/datakeeper/refs/heads/main/deployment/install.sh | sudo sh
```

#### 🔧 With Build from Source (Docker Required)

Build the project from scratch using Docker:

```bash
curl -sSfL https://raw.githubusercontent.com/SUNET/datakeeper/refs/heads/main/deployment/install.sh | bash -s -- --with-build=true
```

---

### **2. Manual Git-Based Installation**

Use this method if you prefer to inspect or modify the installation script before running it.

#### 🛠️ Clone and Run

```bash
git clone --depth=1 https://github.com/SUNET/datakeeper.git 
cd datakeeper/deployment
chmod +x install.sh
less install.sh  # Optional: inspect the script
./install.sh
```

#### 🔧 Build from Source

```bash
./install.sh --with-build=true
```

---

### **3. Run with Poetry (Development Mode)**

For local development and contributions:

1. **Install Poetry**  
   Follow the [official Poetry installation guide](https://python-poetry.org/docs/#installation) if you haven't already.
   Additionally, ensure that you have Python 3.9 installed on your system.

2. **Clone and Set Up Environment**

```bash
git clone https://github.com/SUNET/datakeeper.git
cd datakeeper
poetry install
poetry shell
```

3. **Run the Application**

```bash
poetry run datakeeper --help
```

## Development Dependencies

```bash
poetry add pytest nox black mypy --group dev
```

- **pytest**: For running tests.
- **nox**: For automating testing and other development tasks.
- **black**: For code formatting.
- **mypy**: For static type checking.

```bash
cd datakeeper
poetry shell
poetry install
python main.py --help
```

## pytest

```python
pytest tests/ --verbose -s
```

## Usage

After installation, you can inspect the **DataKeeper** CLI by running:

```bash
datakeeper --help
```

### **Start Monitoring a Specific folder**

To begin monitoring a folder with a specified configuration, use the following command:

```bash
datakeeper schedule --config path/to/config/file
```

### **Example Configuration File**

Here’s an example of what the configuration file might look like:

```ini
[DATAKEEPER]
LOG_DIRECTORY = /tmp/datakeeper
PLUGIN_DIR = /tmp/datakeeper/datakeeper/policy_system/plugins
POLICY_PATH = /tmp/datakeeper/datakeeper/config/policy.yaml
DB_PATH = /tmp/datakeeper/datakeeper/database/database.sqlite
INIT_FILE_PATH = /tmp/datakeeper/datakeeper/database/init.sql
```

For an example of `policy.yaml`, visit check the policy file:  
[Example Policy on GitHub](https://github.com/SUNET/datakeeper/blob/main/datakeeper/config/policy.yaml)

### **Generate Test Data in the Monitored Folder**

To generate test data in the monitored folder, use the following command:

```bash
datakeeper generate --format hdf5 --base-dir [folder-path] --create-dir
```

This will create the necessary directories and generate the data in the specified format (`hdf5`).


