
import os

"""
This module contains the code for the versions class.

The purpose of this module is to construct a view of the physical versions
on disk. Using this information, several items are then derived:

1. What the next revision is going to be (numerically)
2. Which versions need to be groomed in order to adhere to policy
3. Any inconsistencies in the physical v. logial view of the versions
"""

class C_versions:
    def __init__(self,msg,tgt_path):
        """Constructor for the C_versions class. Initialize the
        variables that we need to have in order for the class to
        operate:
        
        verdir  - the absolute path of the versions folder.
        msgout  - the generic message handler for printing output
        pview   - whether the physical view was created OK
        sane    - whether the logical vs. physical views are sane
        pruned  - whether we ran a prune yet.
        dirlist - list of versions we found on disk"""
        
        self.verdir = os.path.abspath(tgt_path)
        self.msgout = msg
        self.pview = False
        self.sane = False
        self.pruned = False
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

    def sanify(self, num_versions, logical_versions):
        """The purpose of sanify is to validate that the physical versions
        on disk match up to the logical view that the config file says we
        should have. If we don't have that, then we do not want to allow a
        backup job to run."""
        
        if not self.pview:
            self.msgout('No physical view for <%s> was found.' % self.verdir)
            return 1
        
        c0 = 0
        c1 = 0

        # The first thing we are going to do is see if any physical directories are
        # present on disk, but were not listed in the buver.conf logical view.
        for version in self.dirlist:
            if version not in logical_versions:
                self.msgout('Found <%s> on disk, but not in config file' % version)
                c0 = c0 + 1
                
        # Now, let's do the opposite. Look for versions that are in the logical view
        # but do not exist on the physical disk ...
        for version in logical_versions:
            if version not in self.dirlist:
                self.msgout('Found <%s> in config file, but not on disk' % version)
                c1 = c1 + 1

        # if the physical vs. logical views are inconsistent, bail. The administrator
        # will have to clean this up so that we do not do bad things ...
        if c0 or c1:
            self.msgout('mismatched physical vs. logical versions ...')
            return 2
        
        # Ok, now let's do a few other things to help the prune and backup processes.
        # determine how many versions we want to keep in our versions folder ...
        keep = num_versions - 1
        
        # if the user wants more than 1 version, then take the number they want - 1.
        # - 1, because we are going to add a new version during this backup run ...
        if keep > 0:
            # this handles the admin changing the number of versions to keep
            # between runs ... in other words, it doesn't just eliminate the oldest
            # version, it eliminates the oldest 'n' versions...
            self.keepers = logical_versions[-keep:]
        else:
            # ok, they only want to keep one version, so empty the list
            self.keepers = []

        # Ok, now if the number of logical versions is > 0 (always true unless
        # this is the first time we are running ...)
        if len(logical_versions) > 0:
            # pick up the ending version number from the keepers list and add 1
            self.keepers.append(str(int(logical_versions[-1]) + 1))
        else:
            # this is the first run, so just put a '1' in the list
            self.keepers.append('1')
        
        # form the directory path where the next version needs to go. This is conveniently
        # stored in self.keepers as the last element. Join the versions path to this, and you
        # have what you need to construct a new version.
        self.nextdir = os.path.join(self.verdir, self.keepers[-1])
        
        # Ok, ultra paranoia here. Make sure the "new" version doesn't exist! This should
        # never happen, but just in case ...
        if os.path.isdir(self.nextdir):
            self.msgout('Internal error: did not expect <%s> to exist ...' % self.nextdir)
            return 3

        # Ok, tell the class that we are now sane and ready to prune if the app so chooses.
        self.sane = True

        return 0
        
    def new_ver_dirs(self):
        """Return the list of the versions that we need to keep.
        This is used to rewrite the config with the proper logical
        view at the end of the backup process."""
        
        if self.sane: return self.keepers
        
        return []   # Yikes! This should never happen, but let's be safe ...
        
    def new_version(self):
        """Return the path where the next version is to be stored."""
        
        if self.sane: return self.nextdir
        
        # this should never happen, unless the program has a logic error ...
        return os.path.join(self.verdir,'INVALID_STATE')
    
    def prune(self):
        """Ok, now let's go remove the old version(s), based on
        the results from the sanify() method."""
        
        if not self.sane:
            self.msgout('The prune() method was invoked in an invalid state.')
            return 1
        
        if self.pruned:
            self.msgout('The prune() method was invoked multiple times...')
            return 2
            
        # For each version on the physical disk ...
        for version in self.dirlist:
            # If we are not supposed to keep it ...
            if version not in self.keepers:
                # Then issue the 'rm -rf ..." command to get rid of it
                command = 'rm -rf "%s"' % os.path.join(self.verdir,version)
                self.msgout(command)
                os.system(command)
                
        # Denote the object state.
        self.pruned = True
        return 0
