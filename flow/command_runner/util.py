from contextlib import contextmanager
import logging
import os

LOG = logging.getLogger(__name__)

@contextmanager
def environment(environment_dicts):
    temporary_environment = dict()
    for env in environment_dicts:
        temporary_environment.update(env)

    for k, v in temporary_environment.iteritems():
        if v is None:
            temporary_environment[k] = ''

    saved_environment = dict(os.environ.data)
    os.environ.clear()

    for key, value in temporary_environment.iteritems():
        LOG.debug('Updating environment variable %s=%s', key, value)
        try:
            os.environ[key] = value
        except UnicodeEncodeError:
            LOG.debug('Failed to update environment variable %s=%s... skipping',
                    key, value)
            pass

    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved_environment)

@contextmanager
def seteuid(user_id):
    if user_id is not None:
        saved_user_id = os.geteuid()
        if user_id != saved_user_id:
            LOG.debug('Setting uid to 0, then to %d', user_id)
            os.seteuid(0)
            os.seteuid(user_id)
        else:
            LOG.debug('Uid is already %d, not changing', user_id)

    try:
        yield
    finally:
        if user_id is not None:
            if saved_user_id != os.geteuid():
                os.seteuid(0)
                os.seteuid(saved_user_id)
                LOG.debug('uid reset to %d', saved_user_id)
            else:
                LOG.debug('Uid is already %d, not changing', user_id)
