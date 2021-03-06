#!/usr/bin/env python
# encoding: utf-8

"""Verify that all OSF Storage files have Glacier backups and parity files,
creating any missing backups.

TODO: Add check against Glacier inventory
Note: Must have par2 installed to run
"""

from __future__ import division

import gc
import os
import math
import hashlib
import logging

import pyrax

from boto.glacier.layer2 import Layer2
from pyrax.exceptions import NoSuchObject

from framework.celery_tasks import app as celery_app

from website.app import init_app
from osf.models import FileVersion

from scripts import utils as scripts_utils
from scripts.osfstorage import utils as storage_utils
from scripts.osfstorage import settings as storage_settings


container_primary = None
container_parity = None
vault = None
audit_temp_path = None


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger('boto').setLevel(logging.CRITICAL)


def delete_temp_file(version):
    path = os.path.join(audit_temp_path, version.location['object'])
    try:
        os.remove(path)
    except OSError:
        pass


def download_from_cloudfiles(version):
    path = os.path.join(audit_temp_path, version.location['object'])
    if os.path.exists(path):
        # we cannot assume the file is valid and not from a previous failure.
        delete_temp_file(version)
    try:
        obj = container_primary.get_object(version.location['object'])
        with open(path, 'wb') as fp:
            hasher = hashlib.sha256()
            fetcher = obj.fetch(chunk_size=262144000)  # 256mb chunks
            while True:
                try:
                    chunk = next(fetcher)
                except StopIteration:
                    break
                hasher.update(chunk)
                fp.write(chunk)
        if hasher.hexdigest() != version.metadata['sha256']:
            raise Exception('SHA256 mismatch, cannot continue')
        return path
    except NoSuchObject as err:
        logger.error('*** FILE NOT FOUND ***')
        logger.error('Exception:')
        logger.exception(err)
        logger.error('Version info:')
        logger.error(version.to_storage())
        return None


def ensure_glacier(version, dry_run):
    if version.metadata.get('archive'):
        return
    logger.warn('Glacier archive for version {0} not found'.format(version._id))
    if dry_run:
        return
    file_path = download_from_cloudfiles(version)
    if file_path:
        glacier_id = vault.upload_archive(file_path, description=version.location['object'])
        version.metadata['archive'] = glacier_id
        version.save()


def check_parity_files(version):
    index = list(container_parity.list_all(prefix='{0}.par2'.format(version.location['object'])))
    vols = list(container_parity.list_all(prefix='{0}.vol'.format(version.location['object'])))
    return len(index) == 1 and len(vols) >= 1


def ensure_parity(version, dry_run):
    if check_parity_files(version):
        return
    logger.warn('Parity files for version {0} not found'.format(version._id))
    if dry_run:
        return
    file_path = download_from_cloudfiles(version)
    if file_path:
        parity_paths = storage_utils.create_parity_files(file_path)
        for parity_path in parity_paths:
            container_parity.create(parity_path)
            os.remove(parity_path)
        if not check_parity_files(version):
            logger.error('Parity files for version {0} not found after update'.format(version._id))


def ensure_backups(version, dry_run):
    ensure_glacier(version, dry_run)
    ensure_parity(version, dry_run)
    delete_temp_file(version)


def glacier_targets():
    return FileVersion.objects.filter(location__has_key='object', metadata__archive__isnull=True)


def parity_targets():
    # TODO: Add metadata.parity information from wb so we do not need to check remote services
    return FileVersion.objects.filter(location__has_key='object')
        # & metadata__parity__isnull=True


def audit(targets, num_of_workers, worker_id, dry_run):
    maxval = math.ceil(targets.count() / num_of_workers)
    target_iterator = targets.iterator()
    idx = 0
    last_progress = -1
    for version in target_iterator:
        if hash(version._id) % num_of_workers == worker_id:
            if version.size == 0:
                continue
            ensure_backups(version, dry_run)
            idx += 1
            progress = int(idx / maxval * 100)
            if last_progress < 100 and last_progress < progress:
                logger.info(str(progress) + '%')
                last_progress = progress
                gc.collect()


@celery_app.task(name='scripts.osfstorage.files_audit')
def main(num_of_workers=0, worker_id=0, glacier=True, parity=True, dry_run=True):
    global container_primary
    global container_parity
    global vault
    global audit_temp_path

    # Set up storage backends
    init_app(set_backends=True, routes=False)

    try:
        # Authenticate to Rackspace
        pyrax.settings.set('identity_type', 'rackspace')
        pyrax.set_credentials(
            storage_settings.USERNAME,
            storage_settings.API_KEY,
            region=storage_settings.REGION
        )
        container_primary = pyrax.cloudfiles.get_container(storage_settings.PRIMARY_CONTAINER_NAME)
        container_parity = pyrax.cloudfiles.get_container(storage_settings.PARITY_CONTAINER_NAME)

        # Connect to AWS
        layer2 = Layer2(
            aws_access_key_id=storage_settings.AWS_ACCESS_KEY,
            aws_secret_access_key=storage_settings.AWS_SECRET_KEY,
        )
        vault = layer2.get_vault(storage_settings.GLACIER_VAULT)

        # Log to file
        if not dry_run:
            scripts_utils.add_file_logger(logger, __file__, suffix=worker_id)

        audit_temp_path = os.path.join(storage_settings.AUDIT_TEMP_PATH, str(worker_id))
        if not dry_run:
            try:
                os.makedirs(audit_temp_path)
            except OSError:
                pass

        if glacier:
            logger.info('glacier audit start')
            audit(glacier_targets(), num_of_workers, worker_id, dry_run)
            logger.info('glacier audit complete')

        if parity:
            logger.info('parity audit start')
            audit(parity_targets(), num_of_workers, worker_id, dry_run)
            logger.info('parity audit complete')

    except Exception as err:
        logger.error('=== Unexpected Error ===')
        logger.exception(err)
        raise err


if __name__ == '__main__':
    import sys
    arg_num_of_workers = int(sys.argv[1])
    arg_worker_id = int(sys.argv[2])
    arg_glacier = 'glacier' in sys.argv
    arg_parity = 'parity' in sys.argv
    arg_dry_run = 'dry' in sys.argv
    main(num_of_workers=arg_num_of_workers, worker_id=arg_worker_id, glacier=arg_glacier, parity=arg_parity, dry_run=arg_dry_run)
