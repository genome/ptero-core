import flow.command_runner.executors.nets as enets
import flow.petri.netbuilder as nb

import test_helpers

class TestLSFDispatchAction(test_helpers.RedisTest):
    def test_response_places(self):
        cmdline = ["ls", "-al"]
        builder = nb.NetBuilder("test")
        net = enets.LSFCommandNet(builder, name="test", cmdline=cmdline)

        expected = {
            'dispatch_success_place': str(net.dispatch_success_place.index),
            'dispatch_failure_place': str(net.dispatch_failure_place.index),
            'begin_execute_place': str(net.begin_execute_place.index),
            'execute_success_place': str(net.execute_success_place.index),
            'execute_failure_place': str(net.execute_failure_place.index),
        }

        stored_net = builder.store(self.conn)
        dispatch_transition = stored_net.transition(0)
        self.assertEqual("dispatch", str(dispatch_transition.name))
        action = dispatch_transition.action
        self.assertIsInstance(action, enets.LSFDispatchAction)

        response_places = action._response_places()
        self.assertEqual(expected, response_places)