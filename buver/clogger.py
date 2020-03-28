
import os

"""
This module contains the code for the logger class.

The purpose of this module is to provide a logger class
for reporting each run of the backup utility.
"""

class C_logger:
    def __init__(self,log_path):
        """Constructor for the C_logger class. Initialize the
        variables that we need to have in order for the class to
        operate:
        
        logpath - the absolute path of the log directory.
        ready   - if we have an open log file"""
        
        self.logpath = os.path.abspath(log_path)
        self.filename = ''
        self.ready = False
        
    def getlogpath(self):
        """returns the fully qualified filename of the current log"""
        if hasattr(self,'filename'): return self.filename
        
        return ''
        
    def openlog(self,mode='w'):
        """open the logfile for writing, and leave it open.
        it will be used throughout the process lifetime."""
        
        rc = 0
        try:
            # Make the new filename using the PID, store it in the log directory
            if self.filename in ['',None]:
                from time import strftime
                self.filename = os.path.join(self.logpath,'%s.%s.log' % (strftime('%Y-%m-%d.%H-%M-%S'),str(os.getpid())))
                
            self.outfile = open(self.filename, mode)
        except IOError:
            rc = 1

        # if we opened the file, then save the let the object know so it will write to it
        if not rc: self.ready = True

    def closelog(self):
        # if the log file is opened, close it
        if self.ready: self.outfile.close()
        
        # take note that we closed it...
        self.ready = False
        
    def message(self,msgout,write_to_log=True,write_to_console=True):
        """Write a message to the screen (if write_to_console==True) and
        also to the logfile (unless write_to_log is False)."""
        
        # If the logfile isn't opened, go ahead and open it.
        if not self.ready: self.openlog()
        
        # If the logfile is open and write_to_log is True ...
        if self.ready and write_to_log:
            # Write the message to the log file
            self.outfile.write("buver: %s\n" % msgout)
            
        # Also print to the screen ...
        if write_to_console: print('buver: %s' % msgout)
        return 0
