"""
Provides FileStorage implementation for MongoDB GridFS.

This is useful for storing files inside a mongodb database.

"""
from __future__ import absolute_import

from datetime import datetime
from pymongo import MongoClient
import gridfs
from bson import ObjectId

from .interfaces import FileStorage, StoredFile
from . import utils


class GridFSStoredFile(StoredFile):
    def __init__(self, file_id, gridout):
        _check_file_id(file_id)
        self._gridout = gridout
        self._closed = False

        metadata_info = {'filename': gridout.filename,
                         'content_type': gridout.content_type,
                         'content_length': gridout.length,
                         'last_modified': None}

        try:
            last_modified = gridout.last_modified
            if last_modified:
                metadata_info['last_modified'] = datetime.strptime(last_modified,
                                                                   '%Y-%m-%d %H:%M:%S')
        except:
            pass

        super(GridFSStoredFile, self).__init__(file_id=file_id, **metadata_info)

    def read(self, n=-1):
        if self._closed:
            raise ValueError("cannot read from a closed file")

        return self._gridout.read(n)

    def close(self):
        self._closed = True
        self._gridout.close()

    @property
    def closed(self):
        return self._closed


class GridFSStorage(FileStorage):
    def __init__(self, mongouri, collection='filedepot'):
        self._cli = MongoClient(mongouri)
        self._db = self._cli.get_default_database()
        self._gridfs = gridfs.GridFS(self._db, collection=collection)

    def get(self, file_or_id):
        fileid = self.fileid(file_or_id)

        try:
            gridout = self._gridfs.get(_check_file_id(fileid))
        except gridfs.errors.NoFile:
            raise IOError('File %s not existing' % fileid)

        return GridFSStoredFile(fileid, gridout)

    def create(self, content, filename=None, content_type=None):
        content, filename, content_type = self.fileinfo(content, filename, content_type)
        new_file_id = self._gridfs.put(content,
                                       filename=filename or 'unknown',
                                       content_type=content_type,
                                       last_modified=utils.timestamp())
        return str(new_file_id)

    def replace(self, file_or_id, content, filename=None, content_type=None):
        fileid = self.fileid(file_or_id)
        fileid = _check_file_id(fileid)

        content, filename, content_type = self.fileinfo(content, filename, content_type)
        if filename is None:
            f = self.get(fileid)
            filename = f.filename
            content_type = f.content_type

        self._gridfs.delete(fileid)
        new_file_id = self._gridfs.put(content, _id=fileid,
                                       filename=filename or 'unknown',
                                       content_type=content_type,
                                       last_modified=utils.timestamp())
        return str(new_file_id)

    def delete(self, file_or_id):
        fileid = self.fileid(file_or_id)
        fileid = _check_file_id(fileid)
        self._gridfs.delete(fileid)

    def exists(self, file_or_id):
        fileid = self.fileid(file_or_id)
        fileid = _check_file_id(fileid)
        return self._gridfs.exists(fileid)


def _check_file_id(file_id):
    # Check that the given file id is valid, this also
    # prevents unsafe paths.
    try:
        return ObjectId(file_id)
    except:
        raise ValueError('Invalid file id %s' % file_id)
