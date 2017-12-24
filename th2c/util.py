from tornado.ioloop import IOLoop


class IOLoopSingleton(type):
    """
    Special singleton metaclass which allows for one instance per ioloop.
    Classes can be initialized with force_instance=True to be guaranteed
    a new instance
    """
    _instances = dict()

    def __call__(cls, *args, **kwargs):
        io_loop = kwargs.get('io_loop', IOLoop.current())
        force_instance = kwargs.get('force_instance', False)

        instance = cls._instances.get(io_loop)
        if force_instance:
            instance = super(IOLoopSingleton, cls).__call__(*args, **kwargs)

        if not instance:
            instance = super(IOLoopSingleton, cls).__call__(*args, **kwargs)
            cls._instances[io_loop] = instance
        return instance