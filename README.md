# Transmission Watcher

## Install

**Note:** Recommended usage is within a virtualenv.

```shell
pip install -e ."
```

```shell
pip install -e ".[test,docs]"
```

## Usage

```shell
transmission-watcher --help
```

```shell
pytest -v -ra --junit-xml=tests/report/report.xml --html=tests/report/report.html --self-contained-html
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

