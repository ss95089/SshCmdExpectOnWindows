import paramiko
from paramiko_expect import SSHClientInteraction
import logging
from termcolor import colored
import sys
import re
import time
import datetime
import argparse
import colorama
colorama.init()

class SshExpect(object):
    def __init__(self, prompt, timeout, hostname, username, password):
        self.logger = logging.getLogger()
        self.prompt = prompt
        self.timeout = timeout
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname=hostname, username=username, password=password)
        self.interact = SSHClientInteraction(self.client, timeout=timeout, display=False)
        self.interact.expect(prompt)
        print(self.interact.current_output)
        self.logger.info(self.interact.current_output)

    def cmd_readline(self):
        self.promptStr = "@"
        print(colored('\n--- Execution Result ---', 'blue', attrs=['bold']))
        print(self.interact.current_output)
        self.logger.info(self.interact.current_output)

        if re.search('.*[\?|\:]\s$', self.interact.current_output):
            self.promptStr = "?"
        else:
            self.promptStr = "@"

    def cmd_sendline(self, cmd, prompt='', timeout=''):
        if prompt == '':
            prompt = self.prompt
        if timeout == '':
            timeout = self.timeout
        self.interact.send(cmd)
        while True:
            res = self.interact.expect(prompt, int(timeout))
            self.cmd_readline()
            if res == 0:
                return(self.promptStr)
            elif res == -1:
                print(colored('\n[TimeOutError] The prompt could not be detected.', 'red'))
                self.logger.error('The prompt could not be detected.')
                while True:
                    input_yn = input('[W]ait/[C]trl+C/[I]nputCmd/[Q]uit: ').upper()
                    if input_yn.upper() == 'W':
                        print(colored('\nwait 10 seconds.', 'red'))
                        time.sleep(10)
                        break
                    elif input_yn.upper() == 'C':
                        break
                    elif input_yn.upper() == 'I':
                        break
                    elif input_yn.upper() == 'Q':
                        sys.exit(1)
                if input_yn.upper() == 'C':
                    self.interact.send(chr(3))
                    time.sleep(1)
                    self.interact.send('')
                    time.sleep(1)
                    self.cmd_sendline('')
                elif input_yn.upper() == 'I':
                    input_cmd = input('Input Command: ')
                    self.interact.send(input_cmd)
                    return(self.promptStr)

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--ip', help='IP Address', required=True)
parser.add_argument('-u', '--username', help='UserName', required=True)
parser.add_argument('-p', '--password', help='Password', required=True)
parser.add_argument('-f', '--file', help='Name of command file to execute', required=True)
parser.add_argument('-r', '--replace', help='String replacement specification. [before str1]:[after str1]@[before str2]:[after str2]', required=False)
args = parser.parse_args()

ipAddress = args.ip
userName = args.username
password = args.password
fileName = args.file
fileName = fileName.replace(".\\", '')
repStr = args.replace

formatter = '\n[%(asctime)s][%(levelname)s]\n%(message)s'
logging.basicConfig(filename='logs/{}_{}_{}.log'.format(ipAddress, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'), fileName), level=logging.INFO, format=formatter)

#prompt = ['.*[0-9]\:[0-9][0-9]\:[0-9][0-9]\][\#|\$|\>]\s']
prompt = '.*[\#|\$|\>|\?|\:]\s$'
timeout = 15
rawLabel = []
flg1 = False

proc = SshExpect(prompt, 5, ipAddress, userName, password)

proc.cmd_sendline(r'export PS1="[\u@\h \W]\\$ "', prompt, timeout)
proc.cmd_sendline(r'export LANG=C', prompt, timeout)

while True:
    with open(fileName, 'r', encoding="utf-8") as file:
        lines = file.readlines()
        i0 = 0
        end = len(lines) - 1
        for i1, c in enumerate(lines):
            if c[:1] == '\t' and c[1:].strip() != "":
                rawLabel.append(i1)
        rs = '@'
        while True:
            if rs == '?':
                input_cmd = input('\nInput Command: ')
                rs = proc.cmd_sendline(input_cmd, prompt, timeout)
                #if rs != '?':
                    #proc.cmd_sendline('echo ${?}', prompt, timeout)
            else:
                flg0 = False
                if lines[i0][:1] != '\t':
                    if lines[i0].strip() != '':
                        if not flg1:
                            print(colored('\n-------- Comment -------\n', 'green', attrs=['bold']), end='')
                        print(colored(lines[i0], 'green'), end='')
                        flg1 = True
                elif lines[i0][1:].strip() != "":
                    flg1 = False
                    cmd = lines[i0][1:].strip()
                    if repStr:
                        tmp01 = repStr.split('@')
                        for i3 in tmp01:
                            cmd = cmd.replace(i3.split(':')[0], i3.split(':')[1])
                    while True:
                        print(colored('\n------------------------', 'red', attrs=['bold']))
                        print('[EXE CMD]:', colored(cmd, 'red', attrs=['bold']))
                        cmd_key = input(' -> ExecuteOn[Enter]/[S]kip/[R]eturn/Re[L]oadFile/[Q]uit: ')
                        if cmd_key == '':
                            cmd_key = 'E'
                            break
                        elif len(cmd_key) >= 2 or cmd_key.upper() == 'S' or cmd_key.upper() == 'R' or cmd_key.upper() == 'L' or cmd_key.upper() == 'Q':
                            break
                    if cmd_key.upper() == 'E':
                        rs = proc.cmd_sendline(cmd, prompt, timeout)
                        #if rs != '?':
                            #proc.cmd_sendline('echo ${?}', prompt, timeout)
                    elif len(cmd_key) >= 2:
                        flg0 = True
                        rs = proc.cmd_sendline(cmd_key, prompt, timeout)
                        #if rs != '?':
                            #proc.cmd_sendline('echo ${?}', prompt, timeout)
                    elif cmd_key.upper() == 'S':
                        pass
                    elif cmd_key.upper() == 'R':
                        flg0 = True
                        for i2, c in enumerate(rawLabel):
                            if c == i0 and i2 == 0:
                                i0 = c
                                print(rawLabel, i0)
                                break
                            elif c == i0:
                                i0 = rawLabel[i2 - 1]
                                break
                    elif cmd_key.upper() == 'L':
                        break
                    elif cmd_key.upper() == 'Q':
                        sys.exit()
                if i0 == end:
                    break
                if not flg0:
                    i0 = i0 + 1
        if cmd_key.upper() == 'L':
            pass
        else:
            break
