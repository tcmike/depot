import importlib


class DepotManager(object):
    """Takes care of managing the whole Depot environment for the application.

    DepotManager tracks the created depots, the current default depot,
    and the WSGI middleware in charge of serving files for local depots.

    While this is used to create the default depot used by the application it can
    also create additional depots using the :meth:`new` method.

    In case you need to migrate your application to a different storage while
    keeping compatibility with previously stored file simply change the default depot
    through :meth:`set_default` all previously stored file will continue to work
    on the old depot while new files will be uploaded to the new default one.

    """
    _default_depot = None
    _depots = {}
    _middleware = None

    @classmethod
    def set_default(cls, name):
        if name not in cls._depots:
            raise RuntimeError('%s depot has not been configured' % (name,))
        cls._default_depot = name

    @classmethod
    def get_default(cls):
        if cls._default_depot is None:
            raise RuntimeError('Not depots have been configured!')
        return cls._default_depot

    @classmethod
    def set_middleare(cls, mw):
        if cls._middleware is not None:
            raise RuntimeError('There is already a WSGI middleware registered')
        cls._middleware = mw

    @classmethod
    def get_middleware(cls):
        if cls._middleware is None:
            raise RuntimeError('No WSGI middleware currently registered')
        return cls._middleware

    @classmethod
    def get(cls, name=None):
        """Gets the application wide depot instance.

        Might return ``None`` if :meth:`configure` has not been
        called yet.

        """
        if name is None:
            name = cls._default_depot
        return cls._depots.get(name)

    @classmethod
    def get_file(cls, path):
        depot_name, file_id = path.split('/', 1)
        depot = cls.get(depot_name)
        return depot.get(file_id)

    @classmethod
    def configure(cls, name, config, prefix='depot.'):
        """Configures the application depot.

        This configures the application wide depot from a settings dictionary.
        The settings dictionary is usually loaded from an application configuration
        file where all the depot options are specified with a given ``prefix``.

        The default ``prefix`` is *depot.*, the minimum required setting
        is ``depot.backend`` which specified the required backend for files storage.
        Additional options depend on the choosen backend.

        """
        if name in cls._depots:
            raise RuntimeError('Depot %s has already been configured' % (name,))

        if cls._default_depot is None:
            cls._default_depot = name

        cls._depots[name] = cls.from_config(config, prefix)
        return cls._depots[name]

    @classmethod
    def make_middleware(cls, app, **options):
        """Creates the application WSGI middleware in charge of serving local files.

        A Depot middleware is required if your application wants to serve files from
        storages that don't directly provide and HTTP interface like
        :class:`depot.io.local.LocalFileStorage` and :class:`depot.io.gridfs.GridFSStorage`

        """
        from depot.middleware import DepotMiddleware
        mw = DepotMiddleware(app, **options)
        cls.set_middleare(mw)
        return mw

    @classmethod
    def _new(cls, backend, **options):
        module, classname = backend.rsplit('.', 1)
        backend = importlib.import_module(module)
        class_ = getattr(backend, classname)
        return class_(**options)

    @classmethod
    def from_config(cls, config, prefix='depot.'):
        """Creates a new depot from a settings dictionary.

        Behaves like the :meth:`configure` method but instead of configuring the application
        depot it creates a new one each time.
        """
        config = config or {}

        # Get preferred storage backend
        backend = config.get(prefix + 'backend', 'depot.io.local.LocalFileStorage')

        # Get all options
        prefixlen = len(prefix)
        options = dict((k[prefixlen:], config[k]) for k in config.keys() if k.startswith(prefix))
        options.pop(prefix+'backend', None)
        return cls._new(backend, **options)

    @classmethod
    def _clear(cls):
        """This is only for testing pourposes, resets the DepotManager status

        This is to simplify writing test fixtures, resets the DepotManager global
        status and removes the informations related to the current configured depots
        and middleware.
        """
        cls._default_depot = None
        cls._depots = {}
        cls._middleware = None

get_depot = DepotManager.get
get_file = DepotManager.get_file
configure = DepotManager.configure
set_default = DepotManager.set_default