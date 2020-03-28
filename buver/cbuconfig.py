
import os

"""
This module contains the code for the backup version config.

The class contains all the supporting routines for manipulating the
buver.conf file. This includes:

    1. The creation code to make a new empty buver.conf
    2. The code to load the buver.conf from disk
    3. The code to validate the directives in buver.conf
    4. The code to write out an updated buver.conf
    5. Wrapper methods to get/set the individual attributes
    
All you really need to do here is pass in a generic message
handler (for printing log and error messages) and the directory
where the buver.conf is located (or is to be located).

The supported directives are:

   Directive           Default    Description
  -------------------------------------------------------------------------------
    'src_dir'            ''       The src_dir (what we are protecting)
    'num_versions'       '10'     The number of versions to keep.
    'type'               'tree'   The backup type (tree, tar, gzip)
    'mailto'             ''       The 'mailto' command
    'ver_dirs'           '[]'     The logical versions we know about
    'nice'               '10'     The 'nice' value to be used during backup
    
    'tree_cmd'           '<os specific>'    The 'copytree' command line (xcopy on windows)
    'tar_cmd'            '<os specific>'    The tar command line
    'gzip_cmd'           '<os specific>'    The gzip command line

    'tree_cmd', 'tar_cmd', and 'gzip_cmd' support rudimentary macro expansion:
    
        $src_dir - expands to the value of 'src_dir'
        $dest_dir - expands to the path where the next version should be stored
        $nice - expands to the current nice value
        $tar_name - expands to the name of the tar file to use
        $gzip_name - expands to the name of the gzip file to use
        
    'mailto' supports additional macro expansion:
    
        $version - the current backup directory being written
        $logfile - the name of the log file we just created
        
    Commands are run with the default working directory set to '$dest_dir'
    
NOTE:

    This class assumes that you have properly locked the semaphore 
    before invoking any of the methods herein. It is not safe if
    multiple processes attempt to invoke the methods!

"""

class C_buconfig:
    def __init__(self,msg,tgt_loc):
        """The constructor for the class. Initialize the required member
        variables:
        
        tgt_loc   - the directory where buver.conf is stored
        msgout    - the generic message handler
        config    - the dictionary to store the attributes
        conf_name - stores the fully qualified path for the buver.conf
        """
        self.tgt_loc = tgt_loc
        self.conf_name = os.path.join(tgt_loc,'buver.conf')
        self.config = {}
        self.msgout = msg
        
    def name(self):     # Return the name of the buver.conf file (fully qualified)
        return self.conf_name
    
    def _getConfigItems(self):
            from sys import version_info
            
            if version_info <= (3,0):
                return self.config.iteritems()

            return self.config.items()

    def _get_attr(self,attr):
        # A generic attribute lookup method used by the opt_* methods below
        # Checks to make sure the attribute is there before returning it. If it
        # is not there, returns an empty string.
        if attr in self.config: return self.config[attr]
        
        return ''
        
    def opt_command(self,version,tarname,gzipname):  # Returns the command line that we need to run
        cmd = self._get_attr('%s_cmd' % self.opt_type())
        if cmd in ['', None]: return ''
        
        cmd = cmd.replace('$src_dir',self.opt_src_dir())
        cmd = cmd.replace('$nice',self.opt_nice())
        cmd = cmd.replace('$dest_dir',version)
        cmd = cmd.replace('$tar_name',tarname)
        cmd = cmd.replace('$gzip_name',gzipname)
        
        return cmd
        
    def opt_type(self):             # Returns the backup type (tree, tar, gzip)
        return self._get_attr('type')
        
    def opt_nice(self):             # Returns the 'nice' value to be used during backup
        return self._get_attr('nice')
        
    def opt_src_dir(self):          # Returns the src_dir (what we are protecting)
        return self._get_attr('src_dir')
        
    def opt_num_versions(self):     # Returns the number of versions to keep.
        return self._get_attr('num_versions')
        
    def opt_mailto(self, version, logpath):           # Returns the 'mailto' command
        cmd = self._get_attr('mailto')
        if cmd in ['', None]: return ''
        
        cmd = cmd.replace('$version',version)
        cmd = cmd.replace('$logfile',logpath)
        
        return cmd
        
    def opt_ver_dirs(self):         # Returns the logical versions we know about
        return self._get_attr('ver_dirs')
        
    def set_ver_dirs(self,new_dirs):    # Allows the logical versions directive to be updated
        # This is used after we do a backup, to record the new "logical versions" that
        # we know about. Do this before invoking save(), so that we remember them
        # the next time we run.
        self.config['ver_dirs'] = new_dirs
        
    def validate(self):
        """This method validates the values of each directive in 
        the buver.conf file. This helps keep things operating in
        a sane manner, especially since the buver.conf is a text
        file that the administrator is required to edit."""
        
        # for each directive we know about
        for key,val in self._getConfigItems():
        
            if key.lower() == 'src_dir':
                # Check if src_dir is blank. Print a message, but do not
                # do anything yet. It will be handled later ...
                if val == '':
                    self.msgout('%s key is required, but is not set' % key)
                    
                if val[0] == '~': val = os.path.expanduser(val)
                # Notice that we convert the path to an absolute path. This is useful
                # because it allows the program to run with any current working directory.
                self.config[key] = os.path.abspath(val)

            elif key.lower() == 'num_versions':
                # Right now, support between 1 and 10 versions. If out of range, fix it. :)
                if val == '' or int(val) < 1 or int(val) > 10:
                    self.msgout('%s key is not specified or out of range (1,10). Setting to 10 ...' % key)
                    self.config[key] = '10'
                    
            elif key.lower() == 'nice':
                # Support positive values between (0,20) for nice
                if val == '' or int(val) < 0 or int(val) > 20:
                    self.msgout('%s key is not specified or out of range (0,20). Setting to 10 ...' % key)
                    self.config[key] = '10'
                    
            elif key.lower() == 'type':
                # We know about tree, tar and gzip. If anything invalid is there, put
                # it back to 'tree' so we won't fail later on. tar or gzip might be better
                # choices for the default...
                if val == '' or val not in ['tree','tar','gzip']:
                    self.msgout('%s key is not specified or not in range (tree,tar,gzip). Setting to tree ...' % key)
                    self.config[key] = 'tree'
                    
            elif key.lower() in ['mailto']:
                pass        # these keys are optional ...

            elif key.lower() == 'ver_dirs':
                # The logical directories that we know about. This directive
                # is special, in that it must conform to Python List syntax.
                if val == '' or val[0] != '[' or val[-1] != ']':
                    self.msgout('%s key is not specified or not formatted properly. Setting to [] ...' % key)
                    self.config[key] = '[]'
                    # If this is invalid, it shouldn't be able to do harm, because
                    # when we try to process the versions, we'll get a failure if
                    # what is in this key does not exactly match the contents on
                    # disk at the time the job runs.
                    
                try:
                    self.logical_versions = eval(self.config['ver_dirs'])
                except:
                    self.msgout('Error evaluting the ver_dirs keyword. Resetting to default ...')
                    self.logical_versions = []
                    # See above message to understand why this isn't a fatal ...
                
            elif key.lower() in ['tree_cmd', 'tar_cmd', 'gzip_cmd']:
                # We know about tree, tar and gzip. If anything invalid is there, put
                # it back to 'tree' so we won't fail later on. tar or gzip might be better
                # choices for the default...
                

                if val in ['',None]:
                    self.msgout('%s key is not specified or not in range (tree,tar,gzip). Defaulting to "# NONE" ...' % key)
                    self.config[key] = '# NONE SET'
                    
            else:
                # Just ignore keys you do not understand. This isn't necessarily
                # the safest thing, but it allows older versions of the programs to
                # use newer versions of the buver.conf file ...
                self.msgout('Found key <%s> but I do not understand it. Ignoring ...' % key)
                
        # Now let's do some sanity checking on 'src_dir'. The
        # main thing we want to do is make sure that we are not
        # trying to nest tgt_loc inside src_dir. That would not be
        # a good thing. :)
        src_dir = self.config['src_dir']        # our src_dir value
        tgt_sub = self.tgt_loc[0:len(src_dir)]  # look at the first len(src_dir) characters of tgt_loc
        if os.name == 'nt':
            # Need to ignore case on Windows file systems only
            src_dir = src_dir.lower()
            tgt_sub = tgt_sub.lower()
            
        if  src_dir == tgt_sub:
            self.msgout('src_dir and tgt_loc cannot be the nested')
            return 1
                    
        elif not os.path.isdir(src_dir):
            self.msgout('Directory <%s> does not exist or you do not have access' % src_dir)
            return 2
                
        return 0
        
    def create(self):
        """This method is used to create a new buver.conf with default values in it.
        Note that the config file created with this method isn't usable until you
        go in and at least set the 'src_dir' directive."""
        
        self.config = {
                    'src_dir':'',
                    'num_versions':'10',
                    'type':'tree',
                    'ver_dirs':'[]',
                    'nice':'10'
                   }

        # The remaining keys must be initialized according to platform
        if os.name == 'nt':
            # Here are the Windows defaults
            self.config['tree_cmd'] = 'xcopy "$src_dir" "$dest_dir" /e'
            self.config['tar_cmd'] = 'tar --force-local -cvf "$tar_name" *'
            self.config['gzip_cmd'] = 'tar --force-local -cvf "$tar_name" *&gzip "$gzip_name"'
            self.config['mailto'] = 'postmail -S "Backup $version" -H smtp-server.cfl.rr.com -f backup@buver.com klowrie@yahoo.com < $logfile'
        elif os.name == 'posix':
            # Here are the UNIX defaults
            self.config['tree_cmd'] = 'nice -n $nice cp -r -p "$src_dir" "$dest_dir"'
            self.config['tar_cmd'] = 'nice -n $nice tar cvf "$tar_name" *'
            self.config['gzip_cmd'] = 'nice -n $nice tar cvf "$tar_name" *;nice -n $nice gzip "$gzip_name"'
            self.config['mailto'] = 'mail -s "Backup $version" klowrie@yahoo.com < $logfile'
        else:
            # If we encounter an unsupported platform, just establish some debug statements
            self.msgout('no logic for os.name=%s' % os.name)
            self.config['tree_cmd'] = '#NO_cp_cmd is set'
            self.config['tar_cmd'] = '#NO_tar_cmd is set '
            self.config['gzip_cmd'] = '#NO_gzip_cmd is set'
            self.config['mailto'] = '#NO_mailto is set'
            
        # Just use the save method, but let it know that it is the create() method that is calling it
        return self.save(1)
        
    def load(self):
        """This method is used to load the configuration from buver.conf.
        It will load and then validate the contents of the buver.conf."""
        
        self.config = {}    # if we have one already, throw it out
        
        # If the file doesn't exist, bail now.
        if not os.path.isfile(self.conf_name): return 1

        # Ok, open the file and process each line we find in there.
        try:
            buconf = open(self.conf_name,"r")

            for line in buconf.readlines():
                # split the line on the '=' sign
                x = line.strip().split('=',1)
                
                # this is not really necessary, but I'm leaving it for now.
                # basically, allow the administrator to comment out a
                # line by using '#' in the first column. The real problem
                # here is that when I write the config back out, I will
                # not remember these commented out lines ... that would
                # be a nice feature for version 2. :)
                if len(x) != 2 or x[0][0] == '#': continue

                # put the key=value pair in the config dictionary
                self.config[x[0]] = x[1]

            # close the file when we have processed all of it.
            buconf.close()

        except IOError:
            return 2

        # Invoke the validation method to make sure that the
        # config is in a sane state ...
        return self.validate()

    def save(self,create=0):
        """writes the contents of the dictionary to a file.

        name - the file to write the line to.
        dict - the dictionary to write

        return values:
            0 - Success
            1 - IO error of some type"""

        rc = 0
        op = 'Writing'
        if create: op = 'Creating'
        
        self.msgout('%s config <%s> ...' % (op, self.conf_name))
        # go ahead and rewrite the buver.conf file ...
        try:
            outfile = open(self.conf_name, 'w')
            
            # For each item in the dictionary ...
            for (key,val) in self._getConfigItems():
                # write out the key=value pair to the file ...
                outfile.write('%s=%s\n' % (key,val))

            # close the file
            outfile.close()

        except IOError:
            rc = 1

        return rc

    def dump(self):
        """A method for dumping the configuration dictionary."""
        
        self.msgout('Dumping the configuration dictionary')
        # print each key=value pair in the dictionary ...
        items = ['type', 'nice', 'num_versions', 'mailto', 'src_dir', 'tree_cmd', 'tar_cmd', 'gzip_cmd']
        
        for item in items:
            self.msgout('  %s=<%s>' % (item,self._get_attr(item)))
            
        for key in self.config.keys():
            if key not in items:
                self.msgout('  %s=<%s>' % (key, self.config[key]))
        
