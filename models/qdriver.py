# -*- coding: utf-8 -*-

import socket
from os import path


class QDriverException(Exception):
    pass

class QDriver(object):
    TIMEOUT = 5
    END = 'END'
    ERROR = 'ERROR'

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(self.TIMEOUT)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.s.close()
       
    def _send_data(self, data, wait_for_ack=True):
        self.s.sendto(data.encode('utf-8'), (self.ip, self.port))
        if wait_for_ack:
            while True:
                rdata, address = self.s.recvfrom(4096)
                if (len(address) >= 2) and (address[0] == self.ip) and (address[1] == self.port):
                    if (len(rdata) == 2) and (rdata[0] == 6) and (rdata[1] == 0):
                        break
                    else:
                        raise QDriverException('The cash register reported an error.')
    
    def _receive_data(self):
        while True:
            rdata, address = self.s.recvfrom(4096)
            if (len(address) >= 2) and (address[0] == self.ip) and (address[1] == self.port):
                break
        if (len(rdata) == 2) and (rdata[0] == 6):
            if rdata[1] == 0:
                return self.END
            else:
                return self.ERROR
        else:
            self.s.sendto(bytearray([6]), (self.ip, self.port))
            return rdata.decode('utf-8')

    def run(self, commands):    
        filename = ''
        for cmd in commands.split('\n'):
            data = cmd.strip().split('=')
            if data:
                if data[0] == 'UPLOAD':                        
                    try:          
                        filename = data[1]  
                        if not path.exists(filename): raise QDriverException("The file to upload to the cash register does not exist.")
                        with open(filename, 'r') as file:
                            for line in file:
                                line = 'U' + line.strip()
                                self._send_data(line)
                    finally:
                        filename = ''
                elif data[0] == 'NEWFILE':
                    filename = data[1]
                elif (data[0] == 'COMMAND'):
                    if data[1] in {'CPX', 'CPD', 'CPM', 'CPB'}:
                        self._send_data(data[1])
                    else:                         
                        try:
                            self._send_data(data[1], False)
                            data = None
                            with open(filename, 'w') as file:
                                while True:
                                    data = self._receive_data()
                                    if data in {self.END, self.ERROR}: break
                                    file.write(f'{data}\n')
                            if data == self.ERROR:
                                with open(filename, 'r') as file:
                                    for line in file:
                                        data = line.split(';')
                                        if len(data) > 5 and ''.join(data[0:5]) == '00000' and data[6] != '0':
                                            raise QDriverException(data[5])
                                raise QDriverException('Error executing command at cash register.')
                        finally:
                            filename = ''

    def upload_file(self, filename):
        return self.run(f'UPLOAD={filename}')
