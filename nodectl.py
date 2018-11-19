#!/usr/bin/env python

'''
Created on Apr 20, 2011

@author: ghimire
@version: 1.0
'''

import os, sys
from cmd import Cmd
import getpass, re
from subprocess import Popen, PIPE

VERSION = '1.0'
JSEXTENSION = '.js'
BOLD = "\033[1m"
RESET = "\033[0;0m"
NODEPATH = ''
NODECTL = sys.argv[0]
RUNDIR = os.getcwd()
PSREGEX = re.compile(r'^\s*([0-9]*)\s*(.*?)\s*node (.*)$')
KILL_SIGNAL = 9

def isDir(inputfile):
    if (os.path.isdir(os.path.join(os.getcwd(), inputfile))):
        return True
    return False

def isJsFile(inputfile):
    if inputfile.lower().endswith(JSEXTENSION) and os.path.isfile(os.path.join(os.getcwd(), inputfile)):
        return True
    return False

def get_cpumem(pid):
    cpumem = []
    for nodepid, nodeuser, nodescript in get_nodes():
        if(str(nodepid) == str(pid)):
            ps_process1 = Popen(['ps', '-eo', 'pid,pcpu'], stdout=PIPE, stderr=PIPE)
            awk_process1_output = Popen([r"awk", "/\s*" + pid + "\s*/{print $2}"], stdin=ps_process1.stdout, stdout=PIPE, stderr=PIPE).communicate()[0]
            ps_process1.stdout.close()
            if awk_process1_output:
                cpumem.append(awk_process1_output.strip())
            else:
                cpumem.append(None)

            ps_process2 = Popen(['pmap', pid], stdout=PIPE, stderr=PIPE)
            awk_process2_output = Popen([r"awk", "/\s*total\s*/{print $2}"], stdin=ps_process2.stdout, stdout=PIPE, stderr=PIPE).communicate()[0]
            ps_process2.stdout.close()
            if awk_process2_output:
                cpumem.append(awk_process2_output.strip())
            else:
                cpumem.append(None)

    return cpumem

def get_dirs():
    return [ directory for directory in os.listdir(os.getcwd()) if isDir(directory) ]

def makebold(msg):
    return BOLD + msg + RESET;

def get_jsfiles():
    return [ inputfile for inputfile in os.listdir(os.getcwd()) if isJsFile(inputfile) ]

def get_jsfilesanddirs():
    return [ inputfile for inputfile in os.listdir(os.getcwd()) if ((isJsFile(inputfile)) or (isDir(inputfile))) ]

def get_nodes():
    nodeinfo = []
    ps_process = Popen(['ps', '-eo', 'pid,user,args', '--sort', 'user'], stdout=PIPE, stderr=PIPE)
    grep_process_output = Popen(['grep', '\s[n]ode'], stdin=ps_process.stdout, stdout=PIPE, stderr=PIPE).communicate()[0]
    ps_process.stdout.close()
    if grep_process_output:
        for line in grep_process_output.splitlines():
            m = re.match(PSREGEX, line)
            if m:
                nodepid = m.group(1)
                nodeuser = m.group(2)
                nodescript = m.group(3)
                nodeinfo.append([nodepid, nodeuser, nodescript])
    return nodeinfo

def get_sockinfo(pid):
    sockinfo = []
    nulldev = open(os.devnull, "w")
    # netstat -plan 2>/dev/null | awk '/[tcp|udp].*pid\/node/{print $4}'
    netstat_process = Popen(['netstat', '-plan'], stdout=PIPE, stderr=nulldev.fileno())
    awk_process_output = Popen([r"awk", "/^[tcp|udp].*\s*" + pid + "\s*\/node/{print $4}"], stdin=netstat_process.stdout, stdout=PIPE, stderr=PIPE).communicate()[0]
    netstat_process.stdout.close()
    if awk_process_output:
        for line in awk_process_output.splitlines():
            sockinfo.append(line)
    return sockinfo

class NodeCtl(Cmd):
    def __init__(self):
        Cmd.__init__(self, 'TAB')
        Cmd.ruler = '-'
        print makebold('Welcome to nodectl v' + VERSION + ' [ghimire]. Type "help" for commands description')

        print 'Searching node... ',
        whereisnode = Popen(["which", "node"], stdout=PIPE, stderr=PIPE).communicate()[0].rstrip()

        if(whereisnode):
            NODEPATH = whereisnode
            print 'Found at ' + NODEPATH
        else:
            print 'Not Found. Exiting...'
            sys.exit(1)

        self.prompt = '{' + os.getcwd() + '} % '

    def default(self, line):
        print 'Command ' + line + ' not found.'

    def postcmd(self, stop, line):
        self.prompt = '{' + os.getcwd() + '} % '

    def precmd(self, line):
        return line.strip()

    def do_cd(self, line):
        try:
            os.chdir(line);
        except OSError:
            print 'Invalid path.'
            pass

    def complete_cd(self, text, line, start_index, end_index):
        dirs = get_dirs()
        dirs.append('..')

        if text:
            return [ directory for directory in dirs if directory.startswith(text) ]
        else:
            return dirs

    def do_clear(self, line):
        os.system('clear')

    def do_help(self, line):
        print '''..|[ ''' + makebold("nodectl") + ''' (v''' + makebold(VERSION) + ''') ]|..''';
        print makebold("cd") + "\t   - change directory";
        print makebold("clear") + "\t   - clear terminal";
        print makebold("help") + "\t   - help (this)";
        print makebold("jls") + "\t   - displays javascript files (-l for listing)";
        print makebold("kill") + "\t   - kill node process by name or pid";
        print makebold("list") + "\t   - list running node process";
        print makebold("ls") + "\t   - displays files and dirs (-l for listing)";
        print makebold("pwd") + "\t   - display current directory";
        print makebold("rehash") + "\t   - rehash nodectl";
        print makebold("restart") + "\t   - restart node processes";
        print makebold("run") + "\t   - run node scripts";
        print makebold("quit") + "\t   - quit nodectl";
        print makebold("whoami") + "\t   - display current user";

    def do_kill(self, line):
        for nodepid, nodeuser, nodescript in get_nodes():
            if((nodepid in line.split()) or (nodescript in line.split())):
                print 'Killing ' + nodescript + '[' + nodepid + ']...',
                try:
                    os.kill(int(nodepid), KILL_SIGNAL)
                except OSError:
                    print 'Error: Operation not permitted.'
                    pass
            print

    def do_list(self, line):
        rows, columns = os.popen('stty size', 'r').read().split()
        running_nodes = get_nodes()
        if running_nodes: print '-' * int(columns)
        else: print 'No running nodes found.'
        for nodepid, nodeuser, nodescript in running_nodes:
            sockinfo = ','.join(get_sockinfo(nodepid))
            cpu, mem = get_cpumem(nodepid)
            print "pid: " + makebold(nodepid) + "\tuser: " + makebold(nodeuser) + "\tsock: " + makebold(sockinfo) + "\tcpu: " + makebold(cpu) + "\tmem: " + makebold(mem) + "\tscript: " + makebold(nodescript + "*")
            print '-' * int(columns)

    def do_ls(self, line):
        line = line.strip()
        for filesanddirs in get_jsfilesanddirs():
            if isJsFile(filesanddirs):
                print makebold('*') + filesanddirs,
                if (line == '-l'): print
            else:
                print BOLD + filesanddirs + RESET,
                if (line == '-l'): print
        if not (line == '-l'): print

    def do_jls(self, line):
        line = line.strip()
        for filesanddirs in get_jsfilesanddirs():
            if isJsFile(filesanddirs):
                print makebold('*') + filesanddirs,
                if (line == '-l'): print
        if not (line == '-l'): print

    def do_pwd(self, line):
        print os.getcwd()

    def do_rehash(self, line):
        os.chdir(RUNDIR)
        os.execl(NODECTL, ' - ')

    def do_restart(self, line):
        nodes_to_restart = line.split(' ')
        for node in nodes_to_restart:
            if isJsFile(node):
                for nodepid, nodeuser, nodescript in get_nodes():
                    if(nodescript in node.split()):
                        try:
                            os.kill(int(nodepid), KILL_SIGNAL)
                        except OSError:
                            print 'Error: Operation not permitted.'
                            pass
                print 'Restarting: node ' + node
                Popen(["node", node], stdout=PIPE, stderr=PIPE, shell=False)

    def do_run(self, line):
        nodes_to_start = line.split(' ')
        for node in nodes_to_start:
            if isJsFile(node):
                print 'Starting: node ' + node
                Popen(["node", node], stdout=PIPE, stderr=PIPE, shell=False)
            else:
                print 'Error! ' + node + ' is not a node script'

    def complete_run(self, text, line, start_index, end_index):
        jsfiles = get_jsfiles()
        if text:
            return [ jsfile for jsfile in jsfiles if jsfile.startswith(text) ]
        else:
            return jsfiles

    def do_quit(self, line):
        print 'Quitting ...'
        sys.exit(0)

    def do_whoami(self, line):
        print getpass.getuser()

if __name__ == '__main__':
    ns = NodeCtl()
    ns.cmdloop()

