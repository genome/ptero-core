import unittest
try:
    from unittest import mock
except:
    import mock

import os
from uuid import uuid4
from flow.util import environment as env_util

class EnvironmentContextManagerTest(unittest.TestCase):
    def test_no_contamination(self):
        name = "test_uuid_%s" % uuid4().hex
        value = "test value!"

        self.assertEqual(os.environ.get(name), None)
        os.environ[name] = value
        self.assertEqual(os.environ.get(name), value)

        with env_util.environment([{}]):
            self.assertEqual(os.environ.get(name), None)
        os.environ.pop(name)

        self.assertEqual(os.environ.get(name), None)

    def test_variables_set(self):
        name = "test_uuid_%s" % uuid4().hex
        value = "test value!"
        env = {name: value}

        self.assertEqual(os.environ.get(name), None)
        with env_util.environment([env]):
            self.assertEqual(os.environ.get(name), value)
        self.assertEqual(os.environ.get(name), None)

    def test_override(self):
        name = "old_test_uuid_%s" % uuid4().hex
        old_value = "old test value!"
        new_value = "new test value!"

        old_env = {name: old_value}
        new_env = {name: new_value}

        self.assertEqual(os.environ.get(name), None)
        with env_util.environment([old_env, new_env]):
            self.assertEqual(os.environ.get(name), new_value)

        self.assertEqual(os.environ.get(name), None)

    def test_exception(self):
        old_env = dict(os.environ.data)

        try:
            with env_util.environment([{}]):
                raise RuntimeError()
        except:
            pass

        self.assertEqual(old_env, os.environ.data)


if '__main__' == __name__:
    unittest.main()
