import logging
from pythonlsf import lsf
from flow.command_runner.executor import ExecutorBase

from flow.command_runner import util

LOG = logging.getLogger(__name__)

class LSFExecutor(ExecutorBase):
    def __init__(self, default_queue='long', **kwargs):
        ExecutorBase.__init__(self, **kwargs)

        self.default_queue = default_queue

    def __call__(self, command_line, net_key=None, response_places=None,
            environment={}, working_directory=None, with_inputs=None,
            with_outputs=False, user_id=None, **kwargs):

        full_command_line = self._make_command_line(command_line,
                net_key=net_key, response_places=response_places,
                with_inputs=with_inputs, with_outputs=with_outputs)

        command_string = ' '.join(map(str, full_command_line))
        LOG.debug("lsf command_string = '%s'", command_string)

        request = self.create_request(working_directory=working_directory,
                **kwargs)
        request.command = command_string

        reply = _create_reply()

        with util.environment([self.default_environment, environment,
                               self.mandatory_environment]):
            try:
                with util.seteuid(user_id):
                    submit_result = lsf.lsb_submit(request, reply)
            except Exception as e:
                LOG.error("lsb_submit failed for command string: '%s'",
                        command_string)
                LOG.exception(e)
                raise RuntimeError(str(e))

        if submit_result > 0:
            LOG.debug('successfully submitted lsf job: %s', submit_result)
            return True, submit_result
        else:
            LOG.debug('failed to submit lsf job, return value = (%s)',
                    submit_result)
            return False, submit_result

    def create_request(self, name=None, queue=None, stdout=None, stderr=None,
            beginTime=0, termTime=0, numProcessors=1, maxNumProcessors=1,
            mail_user=None, working_directory=None, **kwargs):
        request = lsf.submit()
        request.options = 0
        request.options2 = 0
        request.options3 = 0

        if name:
            request.jobName = str(name)
            request.options |= lsf.SUB_JOB_NAME

        if mail_user:
            request.mailUser = str(mail_user)
            request.options += lsf.SUB_MAIL_USER
            LOG.debug('setting mail_user = %s', mail_user)

        if queue:
            request.queue = str(queue)
        else:
            request.queue = self.default_queue
        request.options |= lsf.SUB_QUEUE
        LOG.debug("request.queue = %s", request.queue)

        if stdout:
            request.outFile = str(stdout)
            request.options |= lsf.SUB_OUT_FILE
            LOG.debug('setting job stdout = %s', stdout)
        if stderr:
            request.errFile = str(stderr)
            request.options |= lsf.SUB_ERR_FILE
            LOG.debug('setting job stderr = %s', stderr)

        if working_directory:
            request.cwd = str(working_directory)
            request.options3 |= lsf.SUB3_CWD
            LOG.debug('setting cwd = %s', working_directory)

        request.beginTime = int(beginTime)
        request.termTime = int(termTime)

        request.numProcessors = int(numProcessors)
        request.maxNumProcessors = int(maxNumProcessors)

        request.rLimits = get_rlimits(**kwargs)

        return request



def get_rlimits(max_resident_memory=None, max_virtual_memory=None,
        max_processes=None, max_threads=None, max_open_files=None,
        max_stack_size=None, **kwargs):
    # Initialize unused limits
    limits = [lsf.DEFAULT_RLIMIT
            for i in xrange(lsf.LSF_RLIM_NLIMITS)]

    if max_resident_memory:
        limits[lsf.LSF_RLIMIT_RSS] = int(max_resident_memory)
        LOG.debug('setting rLimit for max_resident_memory to %d',
                max_resident_memory)

    if max_virtual_memory:
        limits[lsf.LSF_RLIMIT_VMEM] = int(max_virtual_memory)
        LOG.debug('setting rLimit for max_virtual_memory to %d',
                max_virtual_memory)

    if max_processes:
        limits[lsf.LSF_RLIMIT_PROCESS] = int(max_processes)
        LOG.debug('setting rLimit for max_processes to %d', max_processes)

    if max_threads:
        limits[lsf.LSF_RLIMIT_THREAD] = int(max_threads)
        LOG.debug('setting rLimit for max_threads to %d', max_threads)

    if max_open_files:
        limits[lsf.LSF_RLIMIT_NOFILE] = int(max_open_files)
        LOG.debug('setting rLimit for max_open_files to %d', max_open_files)

    if max_stack_size:
        limits[lsf.LSF_RLIMIT_STACK] = int(max_stack_size)
        LOG.debug('setting rLimit for max_stack_size to %d', max_stack_size)

    return limits


def _create_reply():
    reply = lsf.submitReply()

    init_code = lsf.lsb_init('')
    if init_code > 0:
        raise RuntimeError("Failed lsb_init, errno = %d" % lsf.lsb_errno())

    return reply
