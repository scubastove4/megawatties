
import subprocess

from datetime import date, datetime
from pathlib import Path

from log import get_logger, prepare_run_log
from dataclasses import dataclass, field
from capture.manifest import Manifest
from shared.filenames import _dates
from manifest import _disk_matches
from volume import copy_file_to_volume, validate_volume_file


logger = get_logger(__name__)
final_filename_template = ''
interim_filename_template = ''


@dataclass
class UploadReport:
    uploaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    missing_file: list[str] = field(default_factory=list)
    missing_manifest: list[str] = field(default_factory=list)

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
    prepare_run_log(now)

    logger.info('upload start=%s end=%s today=%s', start.isoformat(), end.isoformat(), today.isoformat())
    report = UploadReport()
    manifest_path_template = (str(landing / kind) + '/{date}/manifest.json'
                              if kind == 'daily'
                              else str(landing / kind) + '/{date[:6]}/manifest.json')

    for dt in _dates(start, end):
        manifest_path = Path(manifest_path_template.format(date=dt))
        if not manifest_path.exists():
            report.missing_manifest.append(str(manifest_path))
            continue
        manifest = Manifest.load(manifest_path)
        manifest, report = upload_file(manifest=manifest,
                                       report=report,
                                       landing_path=landing)  # do i need to assign the results to report, or does upload_file modify report in place?

        manifest.save(manifest_path)

    return report


def upload_file(*, manifest: Manifest, report: UploadReport, landing_path: Path) -> tuple[Manifest, UploadReport]:
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

        if item.uploaded:
            report.skipped.append(relative_path)
        elif not item.observations or not item.local_exists:
            report.missing_file.append(relative_path) # may want to add a check to see if local_exists status is accurate
        else:  # at this point if there's at least one observation, assume it's downloaded and available to be uploaded
            # if the local copy exists/file is downloaded
                # check if the object exists in the volume
                    # if it does, hash the object and compare to the manifest
                        # if they match, change manifest status to uploaded, but add filename to 'skipped' -> status['skipped'].append(filename)
            if validate_volume_file(relative_path, manifest_hash):
                report.skipped.append(relative_path)
                item.uploaded = True
                continue

            else:
                local_file_path = landing_path / relative_path
                # validate the local file against the manifest hash
                local_validated = validate_local_file(local_file_path, manifest_hash=manifest_hash)
                # failed if they don't match
                if not local_validated:
                    report.failed.append(relative_path)
                    logger.warning(f'Hash of file on disk does not match hash in manifest, file may have been corrupted. File path: {relative_path}')
                    continue

                else:
                    # if they do match, copy the file to the volume
                    copy_status = copy_file_to_volume(local_file_path, relative_path)
                    # hash it, compare the hash to the hash in the manifest

                        # if the hashes match, change the manifest status to uploaded, and add filename to 'uploaded' -> status['uploaded'].append(filename)
                        # if the hashes don't match, add filename to 'failed' -> status['failed'].append(filename)
                pass
            pass

    return manifest, report


def validate_local_file(file_path: Path, manifest_hash: str) -> bool:
    return _disk_matches(file_path, manifest_hash)


if __name__ == '__main__':
    from shared.calendar import AUCKLAND

    s = date(2026, 11, 10)
    e = date(2026, 11, 25)
    t = date.today()
    n = datetime.now(AUCKLAND)
    l = Path('data/landing')
    k = 'daily'
    upload_prices(start=s, end=e, today=t, now=n, landing=l, kind=k)
    pass
