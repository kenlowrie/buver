import os
import time

"""
This module implements the semaphore class which is used by buver.py.

These semaphores are implemented via the operating system's well known
file IO interfaces. In our case, we use the OS open() API along with
the O_CREAT flag, which guarantees that only one process or thread will
ever succeed.

The file is kept open during the entire duration of the process, and
is closed and then removed when the application is ready to give up the
semaphore.

wait() - create a new file in the target directory. keep it open ...
signal() - close the file created during wait(), then remove it
got_sem() - this API is used to return the current lock state

NOTE:

This implementation could cause starvation amongst processes, if
enough processes are simultaneously trying to access the same target
directory. However, this should not be the case in our situation, so
we are not handling that case at this time.
"""

class C_semaphore:
    def __init__(self,path,filename='csemaphore.lock'):
        """Initialize the object by establishing a name for the mutex,
        the path we want to apply the mutex to, and a flag that is
        used to provide a quick state of the object."""
        
        self.sem_name = os.path.abspath(os.path.join(path,filename))
        self.sem_path = path
        self.sem_locked = False
        
    def got_sem(self):
        """This will return the state of the sem_locked flag."""
        
        return self.sem_locked
        
    def wait(self, maxtries = 120):
        """This is the method that obtains the mutex. It will
        keep trying for 'maxtries' seconds, at which point it
        gives up and returns a failure condition.
        
        Returns:
            0 - The semaphore was acquired
            1 - Unable to acquire the semaphore
        """
        
        attempt = 1
        got_it = 0
        
        # If the directory is invalid, then just give up now.
        if not os.path.isdir(self.sem_path): return True

        # Try until we get it or we exceed the max tries ...
        while got_it == 0 and attempt < maxtries:
            try:
                # This will throw an OSError exception when it fails
                self.fd = os.open(self.sem_name,os.O_CREAT|os.O_EXCL)
                
            except OSError:
                # We didn't get it. Increment the number of tries and sleep for 1 second
                attempt = attempt + 1
                time.sleep(1)
                continue
                
            # Woo Hoo! We acquired the semaphore, set our flag so we'll exit
            got_it = 1
            
        if not got_it: return True

        # Record the object state to reflect we own the semaphore
        self.sem_locked = True
        
        return False

    def signal(self):
        """This is the method that releases the mutex.
        
        Returns:
            0 - The semaphore was released
            1 - Unable to release the semaphore
        """
        
        # if the object doesn't reflect that we have the semaphore, bail
        if self.sem_locked == False: return True
        
        # Close the open file handle, catch any exceptions, but basically
        # just print an error and keep going.
        try:
            os.close(self.fd)
        except OSError:
            print('Internal failure during semaphore release - close')
            
        # Remove the file. This will allow the next call to wait() to succeed
        # since the file will no longer exist. Catch any exceptions, but
        # basically ignore them. If we cannot delete it, then that means some
        # manual clean up is going to be required.
        try:
            os.remove(self.sem_name)
        except OSError:
            print('Internal failure during semaphore release - remove')

        # Reflect that we have released our semaphore. This is here so that if
        # the atexit() routine runs and attempts to release the semaphore, we
        # will ignore the request. It isn't useful for anything else.
        self.sem_locked = False
        return False
