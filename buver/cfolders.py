
import os
import string

"""
This module contains the code for the folders class.

The purpose of this module is to construct a list of the folders
on disk at the specified location. Methods are then constructed
to operate on this folder list.

Currently, the implemented methods are:

stripthis() - Removes 'stripme' from all folders in 'tgt_loc'

This isn't implemented correctly. stripthis should take a paramter,
or this class should be a base class, and then other classes can
implement the processing functionality.
"""

class C_folders:
    def __init__(self,msg,stripme,tgt_path):
        """Constructor for the C_folders class. Initialize the
        variables that we need to have in order for the class to
        operate:
        
        verdir  - the absolute path of the versions folder.
        msgout  - the generic message handler for printing output
        pview   - whether the physical view was created OK
        dirlist - list of versions we found on disk"""
        
        self.verdir = os.path.abspath(tgt_path)
        self.stripme = stripme
        self.msgout = msg
        self.pview = False
        self.dirlist = []
        
        # Go ahead and initialize the 'dirlist'. This holds the physical view of versions.
        self.load_disk_versions()
        
    def load_disk_versions(self):
        """Create a view of what the physical disk looks like."""
        
        dirlist = []

        # make sure the path exists, otherwise bail now ...
        if not os.path.isdir('%s' % self.verdir): return -1
        
        # go process all the directories in the versions folder
        for f in os.listdir(self.verdir):
            # Only add directories, not files ...
            if os.path.isdir(os.path.join(self.verdir,f)):
                # do not add '.' or '..'
                if f == '.' or f == '..': continue
                
                # add this directory to our physical versions view
                dirlist.append(f)

        self.dirlist = dirlist  # remember our directory list
        self.pview = True       # set the object state so we know we are good
        
        return 0

    def stripthis(self):
        """Ok, now let's go remove the old version(s), based on
        the results from the sanify() method."""
        
        if not self.pview:
            self.msgout('The prune() method was invoked in an invalid state.')
            return 1
        
        # For each version on the physical disk ...
        for version in self.dirlist:
            # remove stripme from the folder before constructing the path
            oldpath = os.path.join(self.verdir,version)
            newpath = os.path.join(self.verdir,string.replace(version,self.stripme,''))
            #print "%s" % string.replace(os.path.join(self.verdir,version),self.stripme,'')
            command = 'mv "%s" "%s"' % (oldpath,newpath)
            if oldpath != newpath:
                self.msgout(command)
                os.system(command)
                
        # Denote the object state.
        self.pruned = True
        return 0
