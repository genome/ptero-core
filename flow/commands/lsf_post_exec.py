import logging
import os
import sys

from flow.commands.token_sender import TokenSenderCommand

LOG = logging.getLogger(__name__)

class LsfPostExecCommand(TokenSenderCommand):
    @staticmethod
    def annotate_parser(parser):
        parser.add_argument('--net-key', '-n')
        parser.add_argument('--failure-place-id', '-f', type=int)

    def __call__(self, parsed_arguments):
        LOG.debug("Starting POST_EXEC_CMD")

        info = os.environ.get('LSB_JOBEXIT_INFO', None)
        stat = os.environ.get('LSB_JOBEXIT_STAT', None)
        if stat is None:
            LOG.critical("LSB_JOBEXIT_STAT environment variable wasn't set... exiting!")
            os._exit(1)
        else:
            stat = int(stat)

        # we don't currently do migrating/checkpointing/requing so we're not
        # going to check for those posibilities.  Instead we will assume that
        # the job has failed.
        if info is not None or stat != 0:
            return_code = stat >> 8
            LOG.debug("Found return code to be %s", return_code)
            self.send_token(net_key=parsed_arguments.net_key,
                    place_idx=parsed_arguments.failure_place_id,
                    data={"exit_code": return_code})
        else:
            LOG.debug("Process exited normally")