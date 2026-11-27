
import subprocess

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from log import get_logger
from shared.checksums import sha256_hex

logger = get_logger(__name__)

volume_landing = 'dbfs:/Volumes/workspace/emi/landing/'


@dataclass
class VolumeRecord:
    relative_path: str
    trading_date: date
    local_file_path: str
    sha256: str | None = None
    parent_dir: str | None = None
    absolute_path: str | None = None

    def set_paths(self, kind):
        self.set_parent_dir(kind)
        self.set_absolute_path()

    def set_parent_dir(self, kind):
        self.parent_dir = volume_landing + f'{kind}/{self.trading_date}'

    def set_absolute_path(self):
        self.absolute_path = volume_landing + self.relative_path


def validate_volume_file(volume_record: VolumeRecord, manifest_hash: str) -> bool:
    # check if the object exists in the volume
    # if it does, hash the object and compare to the manifest
    args = [
        '/opt/homebrew/bin/databricks', 'fs', 'cat',
        volume_record.absolute_path,
        '--profile', 'megawatties',
    ]

    try:
        completed = subprocess.run(
            args=args,
            capture_output=True,
            check=True,
            timeout=60,
        )
        logger.info(f'File: {volume_record.absolute_path} exists on the Volume.')
        volume_record.sha256 = sha256_hex(completed.stdout)
        logger.info(f'{volume_record.sha256 = }')

    except subprocess.CalledProcessError as e:
        logger.warning(f'Command: `{" ".join(args)}` failed with exit code {e.returncode}: {e.stderr}')
        return False

    except subprocess.TimeoutExpired:
        logger.warning(f'The command: `{" ".join(args)}` timed out.')
        return False

    except FileNotFoundError:
        logger.warning(
            f'Unable to call the Databricks CLI. Add the absolute path to args. Command executed: `{" ".join(args)}`')
        return False

    file_in_volume = True if volume_record.sha256 else False
    logger.info(f'{file_in_volume = }')
    hash_matches = True if manifest_hash == volume_record.sha256 else False
    logger.info(f'{hash_matches = }')
    return file_in_volume and hash_matches


def copy_file_to_volume(volume_record: VolumeRecord) -> bool:
    confirm_or_make_dir(volume_record)
    return _copy_file(volume_record)


def confirm_or_make_dir(volume_record: VolumeRecord) -> None:
    rel_path = Path(volume_record.relative_path)
    kind_and_date_folders = '/'.join(rel_path.parts[0:2])
    dated_folder_volume_path = f'dbfs:/Volumes/workspace/emi/landing/{kind_and_date_folders}'

    if not _confirm_dir(dated_folder_volume_path):
        _make_dir(dated_folder_volume_path)

    return


def _confirm_dir(dated_folder_volume_path: str) -> bool:
    args = [
        '/opt/homebrew/bin/databricks', 'fs', 'ls',
        dated_folder_volume_path,
        '--profile', 'megawatties',
    ]

    try:
        subprocess.run(
            args=args,
            capture_output=True,
            check=True,
            timeout=60,
        )
        logger.info(f'Dated folder already exists on the Volume: {dated_folder_volume_path}.')
        return True

    except subprocess.CalledProcessError as e:
        logger.warning(f'Command: `{" ".join(args)}` failed with exit code {e.returncode}: {e.stderr}')
        return False


def _make_dir(dated_folder_volume_path: str) -> None:
    args = [
        '/opt/homebrew/bin/databricks', 'fs', 'mkdirs',
        dated_folder_volume_path,
        '--profile', 'megawatties',
    ]

    try:
        subprocess.run(
            args=args,
            capture_output=True,
            check=True,
            timeout=60,
        )
        logger.info(f'Dated folder created on the Volume: {dated_folder_volume_path}.')

    except subprocess.CalledProcessError as e:
        logger.warning(f'Command: `{" ".join(args)}` failed with exit code {e.returncode}: {e.stderr}')
        return

    except subprocess.TimeoutExpired:
        logger.warning(f'The command: `{" ".join(args)}` timed out.')
        return

    return


def _copy_file(volume_record: VolumeRecord) -> bool:
    args = [
        '/opt/homebrew/bin/databricks', 'fs', 'cp',
        volume_record.local_file_path,
        volume_record.absolute_path,
        '--profile', 'megawatties',
    ]

    try:
        subprocess.run(
            args=args,
            capture_output=True,
            check=True,
            timeout=60,
        )
        logger.info(f'File: {volume_record.relative_path} written to the Volume.')

    except subprocess.CalledProcessError as e:
        logger.warning(f'Command: `{" ".join(args)}` failed with exit code {e.returncode}: {e.stderr}')
        return False

    except subprocess.TimeoutExpired:
        logger.warning(f'The command: `{" ".join(args)}` timed out.')
        return False

    return True
