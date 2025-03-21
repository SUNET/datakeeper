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

## Development Dependencies

To manage development dependencies, use the following:

```bash
poetry add pytest nox black mypy --group dev
```

These dependencies include:

- **pytest**: For running tests.
- **nox**: For automating testing and other development tasks.
- **black**: For code formatting.
- **mypy**: For static type checking.

