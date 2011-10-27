#!/usr/bin/python
#
# Snap! base class and interface
#
# (C) Copyright 2011 Mo Morsi (mo@morsi.org)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, Version 3,
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import os
import imp

import snap
from snap.osregistry        import OS
from snap.exceptions        import InsufficientPermissionError
from snap.filemanager       import FileManager
from snap.metadata.snapfile import SnapFile

class SnapBase:
    def __init__(self):
        '''initialize snap '''



    def load_backends(self):
        '''
        Initialize the default backends for the targets with the give names.
        The default backends for the local os will be retrieved and the
        corresponding modules will be loaded out of the backends subdirectories
        and target classes instantiated and returned
        '''
        backends = []

        current_os = OS.lookup()
        for target in snap.config.options.target_backends.keys():
            if snap.config.options.target_backends[target]:
                backend = OS.default_backend_for_target(current_os, target)
                snap.config.options.target_backends[target] = backend

                # Dynamically load the module
                backend_module_name = "snap.backends." + target + "." + backend
                class_name =  backend.capitalize()
                backend_module = __import__(backend_module_name, globals(), locals(), [class_name])

                # instantiate the backend class
                backend_class = getattr(backend_module, class_name)
                backend_instance = backend_class()
                backends.append(backend_instance)

        return backends


    def check_permission(self):
        '''
        ensure current user has permissions to run Snap!

        @raises InsufficientPermissionError - if an error occurs when backing up the files
        '''
        if os.geteuid() != 0:
            raise InsufficientPermissionError("Must be root to run this program")

    def backup(self):
        '''
        peform the backup operation, recording installed packages and copying new/modified files
        '''
        if snap.config.options.log_level_at_least('normal'):
            snap.callback.snapcallback.message("Creating snapshot")

        self.check_permission()

        # temp directory used to construct tarball 
        construct_dir = '/tmp/snap-' + snap.config.options.snapfile.replace("/", "-") + ".d"
        FileManager.make_dir(construct_dir)

        backends = self.load_backends()
        for backend in backends:
          backend.backup(construct_dir) # FIXME include/exclude targets support

        SnapFile(snapfile=snap.config.options.snapfile, 
                 snapdirectory=construct_dir,
                 encryption_password=snap.config.options.encryption_password).compress()
        if snap.config.options.log_level_at_least('normal'):
            snap.callback.snapcallback.message("Snapshot completed")

        FileManager.rm_dir(construct_dir)

    def restore(self):
        '''
        perform the restore operation, restoring packages and files recorded
        '''
        if snap.config.options.log_level_at_least('normal'):
            snap.callback.snapcallback.message("Restoring Snapshot")

        self.check_permission()

        # temp directory used to construct tarball 
        construct_dir = '/tmp/snap-' + snap.config.options.snapfile.replace("/", "-") + ".d"
        FileManager.make_dir(construct_dir)

        backends = self.load_backends()
        SnapFile(snapfile=snap.config.options.snapfile,
                 snapdirectory=construct_dir,
                 encryption_password=snap.config.options.encryption_password).extract()

        for backend in backends:
          backend.restore(construct_dir)

        if snap.config.options.log_level_at_least('normal'):
            snap.callback.snapcallback.message("Restore completed")

        FileManager.rm_dir(construct_dir)
