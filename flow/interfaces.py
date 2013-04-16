from abc import ABCMeta, abstractmethod


class IBroker(object):
    __metaclass__ = ABCMeta


class IHandler(object):
    __metaclass__ = ABCMeta


class IOrchestrator(object):
    __metaclass__ = ABCMeta


class IShellCommand(object):
    __metaclass__ = ABCMeta

class ILocalShellCommand(IShellCommand):
    pass

class IGridShellCommand(IShellCommand):
    pass

class IShellCommandExecutor(object):
    __metaclass__ = ABCMeta


class IStorage(object):
    __metaclass__ = ABCMeta


class IServiceLocator(object):
    __metaclass__ = ABCMeta
