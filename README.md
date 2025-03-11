# Transmission Watcher

This python package allows to automatically synchronize completed downloads from
a Transmission client to a Network Attached Storage (NAS) via SMB.

Major features:

- Copies data only when it's needed to avoid unnecessary copy operations
- Designed to prevent data loss, resilient against script/service interruptions,
  restarts, manual deletions, etc.
- Automatically deletes downloads older than 30 days from the Transmission
  client
- Can be installed as a service to ensure automatic operation

## Install

**Note:** Recommended usage is within a virtualenv.

```shell
pip install -e .
```

## Usage

Refer to the command line interface help for the usage and available options:

```shell
transmission-watcher --help
```

## Run as a service

Check out the repository and install package system-wide:

```shell
sudo pip3 install -e .
```

Create a `transmission-watcher.service` file in `/lib/systemd/system/`:

```text
[Unit]
Description=Transmission Watcher Service
After=transmission-daemon.service

[Service]
ExecStart=transmission-watcher
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Reload services:

```shell
sudo systemctl daemon-reload
```

Enable service:

```shell
sudo systemctl enable transmission-watcher
```

Start service:

```shell
sudo systemctl start transmission-watcher
```

## Development & Testing

Install the package with the required extra packages for development and
testing:

```shell
pip install -e ".[test]"
```

### Run the tests

```shell
pytest -ra --junit-xml=tests/build/report.xml --html=tests/build/report.html --self-contained-html
```

Notes:

- Add the `-v` flag for additional (verbose) output.
- Add the `-s` flag to disable all output capturing (useful for immediately
  displaying `print` outputs).
