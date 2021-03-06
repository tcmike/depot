from depot.manager import DepotManager
from .interfaces import DepotFileInfo
import json

class UploadedThumbFile():
    crop_to_size = False

    def __init__(self, file, filename=None):
        self.file = file
        self.filename = filename
        self.thumb_sizes = None
    
    def set_thumb_sizes(self, thumb_sizes):
        self.thumb_sizes = thumb_sizes

    
        

class UploadedFile(DepotFileInfo):
    """Simple :class:`depot.fields.interfaces.DepotFileInfo` implementation that stores files.

    Takes a file as content and uploads it to the depot while saving around
    most file information. Pay attention that if the file gets replaced
    through depot manually the ``UploadedFile`` will continue to have the old data.

    Also provides support for encoding/decoding using JSON for storage inside
    databases as a plain string.

    Default attributes provided for all ``UploadedFile`` include:
        - filename     - This is the name of the uploaded file
        - file_id      - This is the ID of the uploaded file
        - path         - This is a depot_name/file_id path which can
                         be used with :meth:`DepotManager.get_file` to retrieve the file
        - content_type - This is the content type of the uploaded file
        - uploaded_at  - This is the upload date in YYYY-MM-DD HH:MM:SS format
        - url          - Public url of the uploaded file
        - file         - The :class:`depot.io.interfaces.StoredFile` instance of the stored file
    """
    def process_content(self, content, filename=None, content_type=None):
        """Standard implementation of :meth:`.DepotFileInfo.process_content`

        This is the standard depot implementation of files upload, it will
        store the file on the default depot and will provide the standard
        attributes.

        Subclasses will need to call this method to ensure the standard
        set of attributes is provided.
        """

        target_content = content
        thumb_sizes = [(100, 100), (300, 300)]
        if isinstance(target_content, UploadedThumbFile):
            if filename is None:
                filename = target_content.filename
            if target_content.thumb_sizes is not None:
                if len(target_content.thumb_sizes) > 0:
                    thumb_sizes = target_content.thumb_sizes
            target_content = target_content.file

        file_path, file_id = self.store_content(target_content, filename, content_type)
        self['file_id'] = file_id
        self['path'] = file_path

        saved_file = self.file
        self['filename'] = saved_file.filename
        self['content_type'] = saved_file.content_type
        self['uploaded_at'] = saved_file.last_modified.strftime('%Y-%m-%d %H:%M:%S')
        self['_public_url'] = saved_file.public_url
        self['thumb_sizes'] = thumb_sizes

    def store_content(self, content, filename=None, content_type=None):
        file_id = self.depot.create(content, filename, content_type)
        file_path = '%s/%s' % (self.depot_name, file_id)
        self.files.append(file_path)
        return file_path, file_id

    def store_content_related(self, content, filename=None, content_type=None):
        file_id = self.depot.create_related(content, filename, content_type, self.file_id)
        file_path = '%s/%s' % (self.depot_name, file_id)
        self.files.append(file_path)
        return file_path, file_id

    def encode(self):
        return json.dumps(self)

    @classmethod
    def decode(cls, data):
        return cls(json.loads(data))

    @property
    def url(self):
        public_url = self['_public_url']
        if public_url:
            return public_url
        return DepotManager.get_middleware().url_for(self['path'])

    @property
    def depot(self):
        return DepotManager.get(self.depot_name)

    @property
    def file(self):
        return self.depot.get(self.file_id)