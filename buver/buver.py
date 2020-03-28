#!/usr/bin/env python

"""
This module implements the backup versioning utility command line interface.

TS4813 Operating Systems - Course Project
buver - BackUp Versioning utility
Written by: Ken Lowrie

usage: 

    buver <-i | -b> tgt_loc
    
where:

    -i (--init) - initialize the 'tgt_loc' area for first use
    -b (--bu)   - perform a versioned backup
    
    tgt_loc - the target location where versions are kept
              and the configuration data is kept.
              
example:

    buver -b /home/ken/bu/job_a
"""

import os
import sys

from buver.cbuver import C_buver

def message(msgstr): print('buver: %s' % (msgstr))

def parse_args(args):

    mode = 1        # default mode is Backup
    tgt_loc = '.'   # default directory is current directory, seems reasonable as default
    found_mode = False
    found_tgtloc = False
    
    for arg in args:
        if arg.lower() in ['--help', '-?', '-h', '/h', '/?']: usage()   # be nice, support command line help options
        
        # as we parse, the last switch wins (when ambiguous switches are specified)
        # also, remember if they don't select a mode or target loc, and tell them we defaulted
        if arg.lower() in ['--init', '-i']:
            mode = 0
            found_mode = True
        elif arg.lower() in ['--bu', '-b']:
            mode = 1
            found_mode = True
        else:
            tgt_loc = arg
            found_tgtloc = True
            
    if not found_mode:   message('mode not specified, defaulting to backup ...')
    if not found_tgtloc: message('tgt_loc not specified, defaulting to current directory ...')

    # call the class factor for the buver object and give it back to the caller
    return C_buver(mode,tgt_loc)

def buver_entry():
    # assume we have no arguments, but if we do, pass them along
    args = []
    if len(sys.argv) > 1: args = sys.argv[1:]

    # construct a buver object based on the command line parameters
    buver = parse_args(args)
    
    # invoke the execute method on the object, it takes care of all else
    sys.exit(buver.execute())

def usage():
    print(__doc__)  # just print out the modules' docstring
    sys.exit(1)     # bail with non-zero exit code
    
if __name__ == '__main__':
    sys.exit(buver_entry())
