#!/usr/bin/env python

import datetime
import logging
import os
import subprocess
import time


class TransmissionWatcher:

    def __init__(self, local_dir, nas_dir,
                 transmission_auth_file, nas_smb_auth_file,
                 log_file, logging_level=logging.INFO) -> None:
        """Constructor of the TransmissionWatcher object.

        :param local_dir:
            Path to the local dir where Transmission puts the completed
            downloads.
        :type local_dir: string
        :param nas_dir:
            Path to the remote directory where the downloaded content is
            stored.
        :type nas_dir: string
        :param transmission_auth_file:
            Path to the file that stores the Transmission credentials.
        :type transmission_auth_file: string
        :param nas_smb_auth_file:
            Path to the file that stores the remote (NAS) SMB credentials.
        :type nas_smb_auth_file: string
        :param log_file: Path to the log file.
        :type log_file: string
        :param logging_level: The logging level, defaults to logging.INFO.
        :type logging_level: integer
        """
        self._local_dir = local_dir
        self._nas_dir = nas_dir
        self._transmission_auth_file = transmission_auth_file
        self._nas_smb_auth_file = nas_smb_auth_file
        self._logger = logging.getLogger(__name__)
        self._database = None

        logging.basicConfig(filename=log_file, level=logging_level,
                            format='%(asctime)s [%(levelname)s] %(message)s')

        self._logger.info("***")
        self._logger.info("Starting Transmission Watcher Service...")

    def run(self) -> None:
        """This watcher function ensures that completed torrents are copied to
        the NAS.

        The function checks the current state of the Transmission daemon and
        queries the completed torrents. The completed torrents with their
        metadata are compiled into a list. The list is then processed and each
        completed torrent that does not exist on the NAS is copied to the NAS.
        After successful copy, the torrent is marked as 'copied' in the list.

        Upon first run, the completed list becomes the torrent database as-is.
        During consecutive runs, the current completed list retrieved from the
        daemon is compared to the torrent database and this database is updated
        if there is a change in the completed list. This ensures optimal
        execution so that the NAS is only mounted if necessary and already
        copied items are not copied over to the NAS to minimize network
        activity.

        Furthermore, completed torrents that are more than 30 days old
        (provided they already exist on the NAS) are deleted from the
        transmission daemon and thus from the torrent database.

        The method uses `rsync` for optimal copying. If the service is
        restarted (e.g. rebooting the system where this script runs), the
        torrent database needs to be created upon first execution, which means
        that all existing torrents are initially marked for copying, thus all
        completed torrents are marked for copying to the NAS during this first
        run. This is needed to ensures data integrity. Using `rsync` provides
        two benefits: (1) all the identical files of torrents will be ignored
        and (2) all files that are not matching (e.g. a new file or a previous
        copy had been interrupted) will be copied over.

        .. note:: This function needs to be periodically called over time.
        """
        # Get the actual completed torrent list from daemon
        daemon_completed_list = self._get_completed_torrents()
        if daemon_completed_list is None:
            self._logger.error("Cannot access transmission daemon.")
            return

        # If the database does not exist (i.e. upon first execution):
        # Create database based on the current list of completed torrents
        if self._database is None:
            self._logger.info("Database is created from completed list of "
                              "torrents of daemon.")
            self._database = daemon_completed_list

        # Delete all torrents from database that are not in the completed list
        # reported by the daemon; e.g. torrents that have been deleted from
        # the daemon. After this operation, the database will contain only the
        # items that are part of the daemon completed list.
        self._database = [
            db_item for db_item in self._database if db_item['hash'] in [
                daemon_item['hash'] for daemon_item in daemon_completed_list]
        ]

        # Iterate through the completed list of daemon and compare the item
        # with the item in the database:
        # - If the item does not exist, add it to the database
        # - If the item exists: check the number of files downloaded and mark
        #   it for copying if needed and update its metadata in database
        for daemon_item in daemon_completed_list:
            if daemon_item['hash'] not in [db_item['hash']
                                           for db_item in self._database]:
                # If item does not exist: add it to the database
                self._database.append(daemon_item)
            else:
                # If the item exists: check the number of files downloaded and
                # mark it for copying by updating the database metadata (which
                # includes resetting the flag; thus marked for copying)
                index = 0
                for i, db_item in enumerate(self._database):
                    if daemon_item['hash'] == db_item['hash']:
                        index = i
                        break
                if (self._database[index]['have_files']
                        != daemon_item['have_files']):
                    self._database[index] = daemon_item

        # Check for torrents that are marked for copying to NAS
        is_mounted_by_this_service = False
        for torrent in self._database:
            if torrent['copied'] is False:
                # Sanity check: check if torrent file exists locally
                torrent_path_local = os.path.join(self._local_dir,
                                                  torrent['name'])
                if not os.path.exists(torrent_path_local):
                    # Probably transmission has not finished moving the torrent
                    # to the download-dir; simply ignore it until it's there.
                    # In case the torrent data has been deleted (e.g. from the
                    # web interface right after download has completed) just
                    # before arriving here; then simply ignore and continue
                    continue
                # Mount NAS SMB share; simply break and retry next round if
                # fails
                (mount_result, is_mount_executed) = self._mount_nas()
                if mount_result is False:
                    break
                if is_mount_executed is True:
                    is_mounted_by_this_service = True
                # Note: simply perform an rsync, because it will skip already
                # copied files. This brings two benefits: (1) upon service
                # start, every existing torrents will be checked (since their
                # flag is False), but all the identical ones will be ignored
                # and (2) all files that are not matching (e.g. a previous copy
                # had been interrupted) will be copied. Thus, rsync will
                # effectively copy only the required files.
                self._logger.info("Updating: %s", torrent['name'])
                torrent_path_nas = os.path.join(self._nas_dir, torrent['name'])
                time_copy_begin = time.time()
                torrent_source = torrent_path_local + "/" if os.path.isdir(
                    torrent_path_local) else torrent_path_local
                result = subprocess.run(
                    ["rsync", "-avhu", "--exclude=*.part",
                        torrent_source, torrent_path_nas],
                    capture_output=True, check=False, text=True)
                if result.returncode != 0:
                    self._logger.error("Failed to rsync torrent: %s",
                                       torrent['name'])
                else:
                    time_copy_end = time.time()
                    torrent['copied'] = True
                    elapsed_s = round(time_copy_end - time_copy_begin)
                    duration = str(datetime.timedelta(seconds=elapsed_s))
                    self._logger.info(
                        "Updating done. Size: %s %s, Duration: %s",
                        torrent['have_size'], torrent['have_unit'], duration)

        # Check for completed and copied torrents that are > 30 days old
        for torrent in self._database:
            if torrent['copied'] is True:
                finished_date = datetime.datetime.strptime(
                    torrent['date_finished'], "%a %b %d %H:%M:%S %Y")
                finished_days = (datetime.datetime.now() - finished_date).days
                if finished_days > 30:
                    self._logger.info("Removing: %s", torrent['name'])
                    torrent_id = self._get_torrent_id_based_on_hash(
                        torrent['hash'])
                    if torrent_id is not None:
                        subprocess.run(
                            ["transmission-remote",
                             "-N", self._transmission_auth_file,
                             "-t", torrent_id, "--remove-and-delete"],
                            capture_output=True, check=False, text=True)

        # Unmount NAS SMB share only if it had been mounted by this service
        if is_mounted_by_this_service is True:
            self._unmount_nas()

    def _get_torrent_info(self, torrent_id):
        """Get information about a torrent from the daemon.

        The function returns a tuple containing the name, hash, done percentage
        and the finished date of the requested torrent based on its ID.

        :param torrent_id: The ID of the requested torrent.
        :type torrent_id: integer
        :return: Tuple of torrent name, hash, done percentage, date finished;
                 None if torrent cannot be found (i.e. invalid torrent id
                 supplied).
        :rtype: tuple (string, string, integer, string)
        """
        result = subprocess.run(
            ["transmission-remote",
             "-N", self._transmission_auth_file, "-t", torrent_id, "-i"],
            capture_output=True, check=False, text=True)
        if result.returncode != 0:
            return None

        info_lines = result.stdout.splitlines()
        if not info_lines:
            return None

        torrent_name = None
        torrent_hash = None
        torrent_done = None
        date_finished = None

        for info_line in info_lines:
            info_line = info_line.strip()
            if "Name:" in info_line:
                torrent_name = info_line.lstrip("Name:").strip()
            if "Hash:" in info_line:
                torrent_hash = info_line.lstrip("Hash:").strip()
            if "Percent Done:" in info_line:
                torrent_done = info_line.lstrip("Percent Done:").strip()
            if "Date finished:" in info_line:
                date_finished = info_line.lstrip("Date finished:").strip()

        results = (torrent_name, torrent_hash, torrent_done, date_finished)
        return results if None not in results else None

    def _get_torrent_completed_file_count(self, torrent_id):
        """Get the file count of completed files from a torrent.

        This function checks a torrent by its ID and returns the count of the
        files that have already been completed.

        :param torrent_id: The ID of the requested torrent.
        :type torrent_id: integer
        :return: The count of the completed files of the requested torrent.
        :rtype: integer
        """
        result = subprocess.run(
            ["transmission-remote",
             "-N", self._transmission_auth_file, "-t", torrent_id, "-if"],
            capture_output=True, check=False, text=True)
        if result.returncode != 0:
            return 0

        completed_file_count = 0
        info_lines = result.stdout.splitlines()
        for info_line in info_lines[2:]:
            info_line = info_line.strip()
            if "100%" in info_line:
                completed_file_count += 1

        return completed_file_count

    def _get_completed_torrents(self):
        """Get an array of completed torrents from the daemon.

        This function compiles a list containing completed torrents and their
        respective information. Each completed torrent is represented by a set
        containing the torrent name, hash, date finsihed, size, unit of size,
        file count.

        :return: List of completed torrents; each completed torrent is
                 represented by a set containing torrent name, hash, date
                 finsihed, size, unit of size, file count.
        :rtype: list
        """
        result = subprocess.run(
            ["transmission-remote", "-N", self._transmission_auth_file, "-l"],
            capture_output=True, check=False, text=True)
        if result.returncode != 0:
            self._logger.error(result.stderr)
            return None

        completed_torrent_list = []

        torrent_list_lines = result.stdout.splitlines()
        for torrent_line in torrent_list_lines[1:-1]:
            torrent_id = torrent_line.split()[0]
            torrent_have_size = torrent_line.split()[2]
            torrent_have_unit = torrent_line.split()[3]
            torrent_info = self._get_torrent_info(torrent_id)
            if torrent_info is not None:
                (torrent_name, torrent_hash, torrent_done, date_finished) = \
                    torrent_info
                torrent_have_files = self._get_torrent_completed_file_count(
                    torrent_id)
                if (torrent_done is not None) and ("100%" in torrent_done):
                    completed_torrent_item = {
                        'name': torrent_name,
                        'hash': torrent_hash,
                        'date_finished': date_finished,
                        'have_size': torrent_have_size,
                        'have_unit': torrent_have_unit,
                        'have_files': torrent_have_files,
                        'copied': False
                    }
                    completed_torrent_list.append(completed_torrent_item)

        return completed_torrent_list

    def _get_torrent_id_based_on_hash(self, torrent_hash):
        """Get the ID of a torrent based on its hash from the daemon.

        This function is used for looking up a torrent based on its hash from
        the daemon. The ID of a torrent might change, but its hash always
        identifies it uniquely.

        :param torrent_hash: The hash of a torrent to be looked up.
        :type torrent_hash: string
        :return: The ID of the torrent based on its hash if exists; otherwise
                 `None`.
        :rtype: integer
        """
        result = subprocess.run(
            ["transmission-remote", "-N", self._transmission_auth_file, "-l"],
            capture_output=True, check=False, text=True)
        if result.returncode != 0:
            return None

        torrent_list_lines = result.stdout.splitlines()
        for torrent_line in torrent_list_lines[1:-1]:
            torrent_id = torrent_line.split()[0]
            torrent_info = self._get_torrent_info(torrent_id)
            if torrent_info is not None:
                (_, current_hash, _, _) = torrent_info
                if current_hash == torrent_hash:
                    return torrent_id

        return None

    def _mount_nas(self):
        """Mount the SMB share of the NAS.

        This function checks whether the NAS SMB share had been already mounted
        and it only executes the mounting command if needed.

        :return: List of bools. The first bool is True if the share is
                 successfully mounted after executing this function (either it
                 had been already mounted or it was successfully mounted by
                 this function); otherwise False. The second bool is True if
                 the share is mounted by this function.
        :rtype: (bool, bool)
        """
        is_mounted = True
        is_mount_executed = False

        result = subprocess.run(
            ["mount", "-t", "cifs"],
            capture_output=True, check=False, text=True)
        if self._nas_dir not in result.stdout:
            result = subprocess.run(
                ["mount", self._nas_dir],
                capture_output=True, check=False, text=True)
            if result.returncode != 0:
                self._logger.error("NAS SMB share could not be mounted.")
                self._logger.error(result.stderr)
                is_mounted = False
            else:
                self._logger.info("NAS SMB share is successfully mounted.")
                is_mounted = True
                is_mount_executed = True

        return (is_mounted, is_mount_executed)

    def _unmount_nas(self):
        """Unmount the SMB share of the NAS.

        :return: True if the NAS was successfully unmounted; otherwise False.
        :rtype: bool
        """
        result = subprocess.run(
            ["mount", "-t", "cifs"],
            capture_output=True, check=False, text=True)
        if self._nas_dir in result.stdout:
            result = subprocess.run(
                ["umount", self._nas_dir],
                capture_output=True, check=False, text=True)
            if result.returncode != 0:
                self._logger.error("NAS SMB share could not be unmounted.")
                self._logger.error(result.stderr)
            else:
                self._logger.info("NAS SMB share is successfully unmounted.")
                return True

        return False
