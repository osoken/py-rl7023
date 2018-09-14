# -*- coding: utf-8 -*-

import re
from time import sleep
from threading import Thread

import serial


class RL7023Error(Exception):
    def __init__(self):
        super(RL7023Error, self).__init__()


class RL7023RBPasswordRejected(RL7023Error):
    def __init__(self):
        super(RL7023RBPasswordRejected, self).__init__()


class RL7023RBIDRejected(RL7023Error):
    def __init__(self):
        super(RL7023RBIDRejected, self).__init__()


class RL7023ScanFailed(RL7023Error):
    def __init__(self):
        super(RL7023ScanFailed, self).__init__()


class RL7023ConnectionFailed(RL7023Error):
    def __init__(self):
        super(RL7023ConnectionFailed, self).__init__()


class RL7023ReadError(RL7023Error):
    def __init__(self):
        super(RL7023ReadError, self).__init__()


class RL7023(Thread):
    def __init__(self, rb_id, rb_password, dev, baudrate=115200,
                 hook=None, logger=None):
        super(RL7023, self).__init__()
        self.serial = serial.Serial(
            dev, baudrate=baudrate
        )
        self.logger = logger
        self.__set_password(rb_password)
        self.__set_id(rb_id)
        connection_info = self.__set_connection()
        self.ipv6_addr = connection_info['IPv6Addr']
        self.serial.timeout = 5.0
        self.__renew()
        self.__hook = hook if hook is not None else lambda v: None
        self.start()

    def debug_log(self, msg):
        if self.logger is None:
            print(msg)
        else:
            self.logger.debug('data', extra={'data': msg})

    def __set_connection(self):
        for dur in range(4, 15):
            res = self.__scan(dur)
            if all(('Channel' in res, 'Pan ID' in res, 'Addr' in res)):
                self.__write('SKSREG S2 {}\r\n'.format(res['Channel']))
                self.__readline()
                ok = self.__readline().strip()
                if ok != 'OK':
                    continue
                self.__write('SKSREG S3 {}\r\n'.format(res['Pan ID']))
                self.__readline()
                ok = self.__readline().strip()
                if ok != 'OK':
                    continue
                self.__write('SKLL64 {}\r\n'.format(res['Addr']))
                self.__readline()
                res['IPv6Addr'] = self.__readline().strip()
                self.__write('SKJOIN {}\r\n'.format(res['IPv6Addr']))
                self.__readline()
                if ok != 'OK':
                    continue
                ln = self.__read_expected_pattern(r'EVENT 2[45].*')
                if ln.strip().startswith('EVENT 24'):
                    raise RL7023ConnectionFailed()
                elif ln.strip().startswith('EVENT 25'):
                    self.__readline()
                    return res
        raise RL7023ScanFailed()

    def __scan(self, duration):
        self.__write('SKSCAN 2 FFFFFFFF {}\r\n'.format(duration))
        return {
            d[0].strip(): d[1].strip() for d in
            map(lambda x: x.strip().split(':', 1),
                filter(lambda x: x.startswith('  '),
                       self.__read_until(r'EVENT 22.*')))
        }

    def __set_password(self, rb_password):
        self.__write('SKSETPWD C {}\r\n'.format(rb_password))
        self.__readline()
        ok = self.__readline().strip()
        if ok != 'OK':
            raise RL7023RBPasswordRejected()

    def __set_id(self, rb_id):
        self.__write('SKSETRBID {}\r\n'.format(rb_id))
        self.__readline()
        ok = self.__readline().strip()
        if ok != 'OK':
            raise RL7023RBIDRejected()

    def __write(self, s):
        if isinstance(s, bytes):
            return self.serial.write(s)
        if isinstance(s, str):
            return self.__write(s.encode('raw_unicode_escape'))
        return self.__write(bytes(s))

    def __readline(self):
        ln = self.serial.readline().rstrip().decode('unicode_escape')
        self.debug_log(ln)
        return ln

    def __read_until(self, ptrn, exclude_last_line=True):
        while True:
            ln = self.__readline()
            if re.match(ptrn, ln) is not None:
                if not exclude_last_line:
                    yield ln
                raise StopIteration()
            yield ln

    def __read_expected_pattern(self, ptrn):
        while True:
            ln = self.__readline()
            if re.match(ptrn, ln) is not None:
                return ln

    def __renew(self):
        seq = b'\x10\x81\x00\x01\x05\xFF\x01\x02\x88\x01\x62\x01\xE7\x00'
        self.__write(
            'SKSENDTO 1 {} 0E1A 1 {:04X} '.format(
                self.ipv6_addr, len(seq)
            ).encode('utf-8') + seq
        )
        self.__readline()
        self.__readline()
        self.__readline()
        data = self.__readline()
        if not data.startswith('ERXUDP'):
            return self.__renew()
        cols = data.strip().split(' ')
        res = cols[8]
        seoj = res[8:8+6]
        ESV = res[20:20+2]
        if seoj == '028801' and ESV == '72':
            EPC = res[24:24+2]
            if EPC == 'E7':
                self.__latest_value = int(data[-8:], 16)

    def run(self):
        while True:
            self.__renew()
            self.__hook(dict(zip(self.attributes(), self.values())))
            sleep(1)

    def attributes(self):
        return ('power_consumption', )

    def values(self):
        return (self.power_consumption, )

    @property
    def power_consumption(self):
        return self.__latest_value

    def __getitem__(self, attr):
        if attr in self.attributes():
            return getattr(self, attr)
        raise KeyError(attr)
