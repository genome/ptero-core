import logging
import os
import subprocess

from flow.command_runner.executor import ExecutorBase
from flow.command_runner import util

LOG = logging.getLogger(__name__)

class SubprocessExecutor(ExecutorBase):
    def __call__(self, command_line, net_key=None, response_places=None,
            working_directory=None, environment={}, user_id=None,
            stdout=None, stderr=None, with_inputs=None, with_outputs=False,
            **kwargs):

        full_command_line = self._make_command_line(command_line,
                net_key=net_key, response_places=response_places,
                with_inputs=with_inputs, with_outputs=with_outputs)

        with util.environment([self.default_environment, environment,
                               self.mandatory_environment]):
            try:
                if stdout:
                    stdout_fh = open(stdout, 'a')
                else:
                    stdout_fh = None
                if stderr:
                    stderr_fh = open(stderr, 'a')
                else:
                    stderr_fh = None

                LOG.debug('working_directory = %s', working_directory)
                LOG.debug('PATH = %s', os.getenv('PATH'))

                LOG.debug('executing command %r', full_command_line)
                with util.seteuid(user_id):
                    exit_code = subprocess.call(full_command_line,
                            stdout=stdout_fh, stderr=stderr_fh,
                            cwd=working_directory)

            except OSError as e:
                error_message = 'Executor got error number (%d): %s' % (
                        e.errno, os.strerror(e.errno))
                LOG.error(error_message)
                raise RuntimeError(error_message)
            finally:
                if stdout_fh:
                    stdout_fh.close()
                if stderr_fh:
                    stderr_fh.close()

        if exit_code > 0:
            # XXX get error message
            LOG.debug('failed to execute subprocess job, exit_code = %d',
                    exit_code)
            return False, exit_code
        else:
            LOG.debug('succesfully executed subprocess job')
            return True, exit_code
