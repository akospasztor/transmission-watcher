#!/usr/bin/env python

import argparse
import time
from .transmission_watcher import TransmissionWatcher

LOCAL_DIR = "/mnt/exthd/Media"
NAS_DIR = "/mnt/nas/Media"
TRANSMISSION_AUTH = "/home/pi/.transmission_credentials"
NAS_SMB_AUTH = "/home/pi/.smb_credentials"
LOG_FILE = "/home/pi/transmission_watcher.log"
RUN_PERIOD = 5


def main():
    parser = argparse.ArgumentParser(
        description="Transmission Watcher",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        '--local-dir',
        default=LOCAL_DIR,
        help="path to the local directory where transmission puts the "
             "completed downloads")

    parser.add_argument(
        "--nas-dir",
        default=NAS_DIR,
        help="path to the remote directory where the downloaded content is "
             "stored")

    parser.add_argument(
        "--transmission-auth",
        default=TRANSMISSION_AUTH,
        help="path to the file that stores the Transmission credentials")

    parser.add_argument(
        "--nas-auth",
        default=NAS_SMB_AUTH,
        help="path to the file that stores the remote (NAS) SMB credentials")

    parser.add_argument(
        "--log-file",
        default=LOG_FILE,
        help="path to the log file")

    parser.add_argument(
        "--run-period",
        default=RUN_PERIOD,
        help="execution period in seconds")

    args = parser.parse_args()

    watcher = TransmissionWatcher(args.local_dir, args.nas_dir,
                                  args.transmission_auth, args.nas_auth,
                                  args.log_file)
    while True:
        watcher.run()
        time.sleep(args.run_period)


if __name__ == "__main__":
    main()
