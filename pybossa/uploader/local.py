# -*- coding: utf8 -*-
# This file is part of PYBOSSA.
#
# Copyright (C) 2015 Scifabric LTD.
#
# PYBOSSA is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PYBOSSA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PYBOSSA.  If not, see <http://www.gnu.org/licenses/>.
# Cache global variables for timeouts
"""
Local module for uploading files to a PYBOSSA local filesystem.

This module exports:
    * Local class: for uploading files to a local filesystem.

"""
from pybossa.uploader import Uploader
import os
from werkzeug import secure_filename


class LocalUploader(Uploader):

    """Local filesystem uploader class."""

    upload_folder = 'uploads'

    def init_app(self, app):
        """Config upload folder."""
        super(self.__class__, self).init_app(app)
        if app.config.get('UPLOAD_FOLDER'):
            self.upload_folder = app.config['UPLOAD_FOLDER']
        # If we have a relative path convert it to absolute path
        if not os.path.isabs(self.upload_folder):
            abs_path_app_context = os.path.join(app.root_path, self.upload_folder)
            abs_upload_path_pybossa = os.path.join(os.path.dirname(app.root_path), self.upload_folder)  # ../uploads
            # If we have an existing relative path to the app context use this.
            # In PYBOSSA there is normally no pybossa/uploads folder.
            if os.path.isdir(abs_path_app_context):
                self.upload_folder = abs_path_app_context
            # otherwise use the PYBOSSA ../uploads path (standard)
            elif os.path.isdir(abs_upload_path_pybossa):
                self.upload_folder = abs_upload_path_pybossa
            else:
                raise IOError('Local Upload folder is missing: "%s"' % self.upload_folder)

    def _upload_file(self, file, container):
        """Upload a file into a container/folder."""
        try:
            filename = secure_filename(file.filename)
            if not os.path.isdir(os.path.join(self.upload_folder, container)):
                os.makedirs(os.path.join(self.upload_folder, container))
            file.save(os.path.join(self.upload_folder, container, filename))
            return True
        except Exception:
            return False

    def dir_size(self, container):
        path = os.path.join(self.upload_folder, container)
        if not os.path.isdir(path):
            return True
        dir_list = os.scandir(path)
        total_size = total_count = 0
        for file_size in dir_list:
            total_size += file_size.stat().st_size
            total_count += 1
        if total_count > 20 or total_size > 10000000:
            return False
        return True

    def delete_file(self, name, container):
        """Delete file from filesystem."""
        try:
            path = os.path.join(self.upload_folder, container, name)
            os.remove(path)
            return True
        except Exception:
            return False

    def file_exists(self, name, container):
        """Check if a file exists in a container"""
        try:
            path = os.path.join(self.upload_folder, container, name)
            return os.path.isfile(path)
        except Exception:
            return False


    def delete_img(self, container):
        # 이미지 업로드 후 일정시간이 지날 때 이미지 삭제
        import shutil
        from datetime import datetime
        path = os.path.join(self.upload_folder, container)
        if not os.path.isdir(path):
            return
        file_list = os.listdir(path)

        for f in file_list:
            f = os.path.join(path, f)
            if os.stat(f).st_mtime < datetime.now().timestamp() - (60 * 60 * 7):
                try:
                    os.remove(f)
                    return True
                except Exception:
                    return False
