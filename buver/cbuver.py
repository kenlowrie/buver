
"""
This class implements the backup versioning utility high level methods.

This includes the following:

    __init__   - The class constructor
    tgt_clean  - An atexit method for releasing the semaphore
    mkdir      - A helper method to create a new directory
    check_dir  - A helper method to validate the tgt_loc
    initialize - The code that runs the --init logic of buver
    backup_version - The code that performs a single backup
    backup     - The code that runs the --bu logic of buver
    mailer     - The code that sends an email upon job completion
    execute    - The code that figures out whether to run initialize or backup

Each method has additional documentation in-line.

This module is self-contained. That is, rather than using the
command line version of buver (in buver.py), you could create
a higher level custom application and simply build upon this
class (and it's underlying classes).
"""

import os
import sys

from buver.cbuconfig import C_buconfig
from buver.cversions import C_versions
from buver.csemaphore import C_semaphore
from buver.clogger import C_logger

class C_buver:
    def __init__(self,mode,tgt_loc):
        """Constructor for the C_buver class.
        
        mode    - 0 or 1 for initialize or backup
        tgt_loc - the tgt_loc area"""

        # validate and correct the mode if necessary (default is backup)
        if mode < 0 or mode > 1: mode = 1
        self.mode = mode
        if mode == 0:
            self.mode_str = 'initialize'
        else:
            self.mode_str = 'backup'

        # Initialize a few other useful items (the message API and our PID)
        self.pid = os.getpid()
        
        # Now setup some class variables to store the tgt_loc, the log directory and the version directory
        self.tgt_loc = os.path.abspath(tgt_loc)
        self.tgt_logs = os.path.join(self.tgt_loc,'logs')
        self.tgt_versions = os.path.join(self.tgt_loc,'versions')
        
        # Construct a logger object for printing messages
        self.logger = C_logger(self.tgt_logs)
        self.message = self.logger.message
        
        # Construct a semaphore object for implementing a mutex on tgt_loc
        self.semaphore = C_semaphore(tgt_loc,'buver.lock')
        
        # Register our atexit routines to clean up things ...
        import atexit
        atexit.register(self.logger.closelog)
        atexit.register(self.tgt_clean) # in case we exit without releasing the mutex
        
    def tgt_clean(self):
        """A registered atexit() method that will release our mutex
        if we are trying to exit without first having called signal()!"""
        
        self.message('Clean up procedure for object has been called')
        if hasattr(self,'semaphore'): self.semaphore.signal()

    def mkdir(self,dir):
        """Create directory.  Handles exceptions.
        Returns 0 on success or 1 otherwise."""

        rc = 0
        try:
            os.mkdir(dir)
        except OSError:
            rc = 1

        return rc

    def check_dir(self,dir):
        """A helper that will do a quick sanity on a new tgt_loc
        directory to make sure it is suitable for use. To be
        suitable, it must not exist or be empty."""
        
        if not os.path.isdir(dir): return -1,-1     # -1,-1 means it doesn't exist
        
        dircount  = 0
        filecount = 0
        for f in os.listdir(dir):   # process each item in the tgt_loc directory
            if os.path.isdir(os.path.join(dir,f)):
                # '.' and '..' do not count!
                if f == '.' or f == '..': continue
                
                # we found a directory
                dircount = dircount + 1
            else:
                # we found a file
                filecount = filecount + 1

        # return the directory and file counts
        return dircount,filecount

    def initialize(self):
        """This method implements the logic for the -i command line switch.
        -i causes the tgt_loc directory to be initialized so that it can be
        used for storing backup versions. It must not exist or be an empty
        directory, otherwise it will not be initialized."""
        
        # First, see if the tgt_loc currently exists
        dc,fc = self.check_dir(self.tgt_loc)
        
        if dc == -1:
            # create the tgt_loc area because it does not exist
            self.message('The directory %s does not exist ... creating ...' % self.tgt_loc)
            if self.mkdir(self.tgt_loc):
                self.message('Unable to create directory. Cannot continue ...')
                return 1
                
        elif dc > 0 or fc > 0:
            # either directories or files were found inside tgt_loc. We cannot use this area ...
            self.message('Directory %s is not empty ... cannot initialize directory' % self.tgt_loc)
            return 2
            
        # Ok, the directory exists and we want to initialize it. Get the mutex ...
        if self.semaphore.wait(): 
            self.message('Unable to acquire the semaphore ... exiting ...')
            return 3
            
        # Go ahead and create the 'logs' and 'versions' directories, because they need to be there
        if self.mkdir(self.tgt_logs) or self.mkdir(self.tgt_versions):
            self.message('Unable to create logs or versions directories ... exiting ...')
            return 4
        
        # Ok, the directories are there, create an empty config object
        self.config = C_buconfig(self.message, self.tgt_loc)
        
        # Now create a default buver.conf so the user can finish the configuration
        rc = self.config.create()
        
        # if the create method was successful, tell the user what to do next
        if rc == 0:
            self.message('tgt_loc <%s> has been initialized.' % self.tgt_loc)
            self.message('Edit buver.conf to finish the configuration')

        # Be a good process, and release the semaphore in case someone else needs it
        if self.semaphore.signal(): self.message('Unable to release the semaphore ...')
        
        return rc
        
    def backup_version(self):
        """This method implements the actual backup version
        logic for both the Windows and POSIX platforms."""

        # make sure we set the current directory to the src_dir
        if os.chdir(self.config.opt_src_dir()):
            self.message('Failed changing to the source directory <%s>' % self.config.opt_src_dir())
            return 9999
       
	# print 'Enter a comment for the logfile:'
        # self.message('RUN__ID <%s>' % sys.stdin.readline().strip(),True,False)

        # construct values for the tar_archive name and the gzip_archive name
        tar_archive = '%s' % (os.path.join(self.versions.new_version(), 'backup.tar'))
        gzip_archive = tar_archive
        
        # now expand the command based on the current version and filenames we need to use
        cmd_str = self.config.opt_command(self.versions.new_version(),tar_archive,gzip_archive)
        
        # if we get back an empty string, then we either have an invalid command or something went wrong
        if cmd_str in ['', None]:
            self.message('Unable to get command string for "%s"' % self.config.opt_type())
            return 9999
            
        # commands that start with '#' just get echo'd to the console. Debug feature...
        if cmd_str.strip()[0] == '#':
            self.message('COMMENT <%s>' % cmd_str[1:])
            return 0
        
        # Ok, let's go ahead an execute this command
        self.message('EXECUTE <%s>' % cmd_str)
        return os.system(cmd_str)
        
    def backup(self):
        """This is the method that implements the -b command line switch. -b
        is used to run a backup, using the information in the tgt_loc area;
        buver.conf contains the high level configuration data, and the versions
        directory contains all the versions currently being stored there."""
        
        # The first thing we have to do is obtain the semaphore for the tgt_loc
        if self.semaphore.wait(): 
            self.message('Unable to acquire the semaphore ... exiting ...')
            return 1
        
        # Next, create a config object that holds what we need to know about the tgt_loc
        self.config = C_buconfig(self.message, self.tgt_loc)

        # Now, load the config file and validate the contents
        if self.config.load():
            self.message('Failed loading the configuration file <%s> ... exiting ...' % self.config.name())
            self.semaphore.signal()
            return 2

        # dump the contents to the screen 
        self.config.dump()

        # Now construct the versions object so we can see what is on-disk
        self.versions = C_versions(self.message,self.tgt_versions)
    
        # Make sure that everything looks sane ...
        if self.versions.sanify(int(self.config.opt_num_versions()),self.config.logical_versions):
            self.message('Sanification has failed ... exiting ...')
            return 3
        
        # Prune old directories according the policy set in buver.conf
        if self.versions.prune():
            self.message('prune process has failed cleaning old versions ... exiting ...')
            return 4
        
        # Add a new version to the tree 
        if self.mkdir(self.versions.new_version()):
            self.message('create version directory has failed ... exiting ...')
            return 5
            
        # do the backup
        if self.backup_version():
            self.message('failed during backup_version ... exiting ...')
            # fall through so we update the config file, since we made the directory ...
            
        # Update the config file and write it out
        self.config.set_ver_dirs(self.versions.new_ver_dirs())

        # MAKE SURE WE DO THE, EVEN IF THE BACKUP FAILS, 
        # OTHERWISE, WE'LL INVALIDATE THE VERSIONS AREA!
        if self.config.save():
            self.message('Failed updating the config file ... exiting ...')
            return 6
        
        # Be a good process, and release the semaphore in case someone else needs it
        if self.semaphore.signal(): self.message('Unable to release the semaphore ...')
        
    def mailer(self):
        """This method sends an email on the results of the backup job,
        if a mailto: address has been specified in the buver.conf."""
        
        new_ver = self.versions.new_version()
        log_fil = self.logger.getlogpath()
        
        if not new_ver or not log_fil: 
            self.message('Unable to send email due to missing version or logfile')
            return 0
        
        mail_cmd = self.config.opt_mailto(self.versions.new_version(),self.logger.getlogpath())
        if not mail_cmd: return 0
        
        self.message('MAIL: %s' % mail_cmd)
        self.logger.closelog()
        rc = os.system(mail_cmd)
        self.logger.openlog('a')
        return rc
        
    def execute(self):
        """This method is the driver for the class. Basically, invoke this to
        process whatever the user asked for via the command line options. Do
        a check to provide a hint if the user is trying to run the program
        from an invalid location."""
        
        # generic start message - this will always print
        self.message('Running %s job on directory %s' % (self.mode_str,self.tgt_loc))
        
        # if the mode is 0, then the user is requesting an initialization on the tgt_loc directory
        if self.mode == 0: return self.initialize()
        
        # The only other mode is 1, and that is backup. Before we do that, make sure that the tgt_loc
        # looks like a valid tgt_loc!
        if not os.path.isfile(os.path.join(self.tgt_loc,'buver.conf')):
            self.message('Missing the buver.conf in the tgt_loc <%s>' % self.tgt_loc)
            return 1

        # Invoke the backup method ot do the work
        rc = self.backup()
        
        # Send an email if we need to based on buver.conf:mailto directive
        self.mailer()
        return rc
