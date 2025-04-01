# Deployment short

## Build stand-alone executables

### Dependencies

```sh
poetry add pyinstaller --group dev
poetry add nuitka --group dev
```

### Pyinstaller

```sh
pyinstaller --onefile --name scheduler --hidden-import=pytz scheduler.py
```

```sh
pyinstaller --onefile --name=datakeeper \
  --add-data "datakeeper/database/init.sql:datakeeper/database" \
  --add-data "datakeeper/policy_system/plugins:datakeeper/policy_system/plugins" \
  --add-data "VERSION:." \
  main.py
```

### Nuitka

```sh
nuitka --onefile --standalone --python-flag=no_site \
  --output-filename=datakeeper --output-dir=nuitka-build \
  --include-data-file=datakeeper/database/init.sql=datakeeper/database/init.sql \
  --include-data-dir=datakeeper/policy_system/plugins=datakeeper/policy_system/plugins \
  --include-data-file=VERSION=VERSION \
  main.py
```

### Checks

```sh
chmod +x nuitka-build/datakeeper
./nuitka-build/datakeeper --version
```

**Verify Compatibility Across Linux Distributions**
To check which libraries your executable needs:

```sh
ldd nuitka-build/datakeeper
```

If you see `not found` errors, you may need static linking:

```sh
nuitka --static-libpython=yes --onefile myscript.py
```

This helps make it more portable.

**Test on Different Distributions**
Copy `nuitka-build/datakeeper` to a different Linux machine (Debian, Ubuntu, openSUSE, Arch) and test:

```sh
./datakeeper
```

If any errors occur (e.g., missing `glibc` versions), consider building on an **older** system like Debian 10 for better compatibility.

## Installable exec

2. **Create a Systemd Service Unit File** (`/etc/systemd/system/datakeeper.service`):

```
[Unit]
Description=APScheduler Background Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/scheduler.py
WorkingDirectory=/path/to
Restart=always
User=youruser
Group=yourgroup

[Install]
WantedBy=multi-user.target
```

3. **Enable and Start the Service:**

```sh
sudo systemctl daemon-reload
sudo systemctl enable datakeeper
sudo systemctl start datakeeper
sudo systemctl status datakeeper
```


## Build

```sh
docker compose up --build
```
