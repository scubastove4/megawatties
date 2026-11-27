
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from capture.manifest import Manifest
from log import get_logger
from manifest import _disk_matches
from shared.filenames import _dates
from volume import copy_file_to_volume, validate_volume_file, VolumeRecord


logger = get_logger(__name__)


@dataclass
class UploadReport:
    uploaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    missing_manifest: list[str] = field(default_factory=list)
    missing_file: list[str] = field(default_factory=list)

# for each date in the provided date range
    # if the manifest file is not found, add to the missing_manifest list
    # if the manifest is found
        # if the final file is not downloaded, skip trying to load the final file and add to the missing_file list
        # if the final file is downloaded and is already uploaded, skip the final file and add to the skipped list
        # if the final file is downloaded but is not uploaded, upload the final file
            # if the upload succeeds, mark the file as uploaded and add to the uploaded list
            # if the upload fails, leave the uploaded flag as false and add to the failed list
        # if the interim file is not downloaded, skip trying to load the interim file and add to the missing_file list
        # if the interim file is downloaded and is already uploaded, skip the interim file and add to the skipped list
        # if the interim file is downloaded but is not uploaded, upload the interim file
            # if the upload succeeds, mark the file as uploaded and add to the uploaded list
            # if the upload fails, leave the uploaded flag as false and add to the failed list
        # if interim and final files are available and neither are uploaded, always upload both files
            # one of the gold tables will compare final and interim files, so the interim should always be loaded if available
        # if interim and final files are available and only one is uploaded, always upload whichever is not uploaded yet
            # same as above - one of the gold tables will compare final and interim files, so the interim should always be loaded if available
        # if any upload fails, add the file to the failed list
            # do not fail upload_prices, continue with the next file
    # return the report

    # each step should be logged
    # failed runs should not fail the process, but if all uploads fail a very clear warning should be logged
    # retries on failed uploads will be a future implementation
    # if i'm logging missing/failed *interim* files here, should i also log them in download_prices?
        # i chose not to because it clogs the logs,
        # but since i will have a gold table to compare final and interim files,
        # it might make sense to log issues here and in download_prices


def upload_prices(
        *,
        start: date,
        end: date,
        today: date,
        now: datetime,
        landing: Path,
        kind: str = 'daily'
) -> UploadReport:

    logger.info('upload start=%s end=%s today=%s', start.isoformat(), end.isoformat(), today.isoformat())
    report = UploadReport()
    manifest_path_template = (str(landing / kind) + '/{date}/manifest.json'
                              if kind == 'daily'
                              else str(landing / kind) + '/{date[:6]}/manifest.json')

    for dt in _dates(start, end):
        logger.info(f'Copying local file to Volume for trading date: {dt}.')
        manifest_path = Path(manifest_path_template.format(date=dt))
        if not manifest_path.exists():
            report.missing_manifest.append(str(manifest_path))
            logger.warning(f'Manifest does not exist at this path: {manifest_path}')
            continue
        logger.info(f'Manifest found at {manifest_path}, loading Manifest.')
        manifest = Manifest.load(manifest_path)
        manifest, report = upload_file(manifest=manifest,
                                       report=report,
                                       landing_path=landing,
                                       kind=kind,
                                       dt=dt)  # do i need to assign the results to report, or does upload_file modify report in place?

        manifest.save(manifest_path)

    logger.info(
        'Upload finished uploaded=%s skipped=%s failed=%s missing_manifest=%s missing_file=%s',
        len(report.uploaded),
        len(report.skipped),
        len(report.failed),
        len(report.missing_manifest),
        len(report.missing_file),
    )

    return report


def upload_file(*, manifest: Manifest, report: UploadReport, landing_path: Path, kind: str, dt: date) -> tuple[Manifest, UploadReport]:
    # loop through manifest files
    # return status of each filename
        # if file is uploaded, skip, filename to 'skipped' -> status['skipped'].append(filename)
        # if file is not uploaded
            # if file is not downloaded, add filename to 'missing_file' -> status['missing_file'].append(filename)
            # if the local copy doesn't exist, add filename to 'missing_file' -> status['missing_file'].append(filename)
                # consider adding a check to see if the file is available locally despite the flag stating it's not
            # if the local copy exists/file is downloaded
                # check if the object exists in the volume
                    # if it does, hash the object and compare to the manifest
                        # if they match, change manifest status to uploaded, but add filename to 'skipped' -> status['skipped'].append(filename)
                # validate the local file against the manifest hash
                    # failed if they don't match
                    # if they don't match or there's not file, copy the file to the volume, hash it, compare the hash to the hash in the manifest
                        # if the hashes match, change the manifest status to uploaded, and add filename to 'uploaded' -> status['uploaded'].append(filename)
                        # if the hashes don't match, add filename to 'failed' -> status['failed'].append(filename)
    # return status

    for item in manifest.files.values():
        relative_path = item.relative_path
        manifest_hash = item.sha256

        local_file_path = landing_path / relative_path
        volume_record = VolumeRecord(relative_path=relative_path, trading_date=dt,
                                     local_file_path=str(local_file_path))
        volume_record.set_paths(kind)

        if not item.observations or not item.local_exists:
            report.missing_file.append(relative_path) # may want to add a check to see if local_exists status is accurate
            logger.info(f'File at {relative_path} does not exist, skipping copy.')
        else:  # at this point if there's at least one observation, assume it's downloaded and available to be uploaded
            # if the local copy exists/file is downloaded
                # check if the object exists in the volume
                    # if it does, hash the object and compare to the manifest
                        # if they match, change manifest status to uploaded, but add filename to 'skipped' -> status['skipped'].append(filename)

            if validate_volume_file(volume_record, manifest_hash):
                report.skipped.append(relative_path)
                if not item.uploaded:
                    item.uploaded = True
                    logger.info(f'File existed on volume but was marked as uploaded = False. Updated status to True.')
                logger.info('Skipping copy to the Volume.')
                continue

            else:
                # validate the local file against the manifest hash
                # failed if they don't match
                logger.info('File does not exist on the Volume or existing version is corrupted, proceeding with the copy.')
                if not validate_local_file(local_file_path, manifest_hash=manifest_hash):
                    report.failed.append(relative_path)
                    logger.error(f'Hash of file on disk does not match hash in manifest, local file may have been corrupted. File path: {relative_path}')
                    continue

                else:
                    # if they do match, copy the file to the volume
                    copy_status = copy_file_to_volume(volume_record)

                    # if it fails, log the fail and add to failed in UploadReport
                    if not copy_status:
                        report.failed.append(relative_path)
                        logger.error(f'Copy of {relative_path} to the Volume failed.')
                        continue

                    # hash it, compare the hash to the hash in the manifest
                    if not validate_volume_file(volume_record, manifest_hash):
                        # if the hashes don't match, add filename to 'failed' -> status['failed'].append(filename)
                        report.failed.append(relative_path)
                        logger.error(f'File {relative_path} copied to the Volume, but hash does not match hash in manifest - Incomplete.')
                        continue

                    # if the hashes match, change the manifest status to uploaded, and add filename to 'uploaded' -> status['uploaded'].append(filename)
                    logger.info(f'Copy of {relative_path} to the Volume succeeded.')
                    report.uploaded.append(relative_path)
                    item.uploaded = True

    return manifest, report


def validate_local_file(file_path: Path, manifest_hash: str) -> bool:
    return _disk_matches(file_path, manifest_hash)


if __name__ == '__main__':
    from shared.calendar import AUCKLAND
    from log import prepare_run_log

    s = date(2026, 11, 10)
    e = date(2026, 11, 13)
    t = date.today()
    n = datetime.now(AUCKLAND)
    l = Path('data/landing')
    k = 'daily'

    prepare_run_log(n)

    upload_prices(start=s, end=e, today=t, now=n, landing=l, kind=k)
