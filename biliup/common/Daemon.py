import asyncio
import logging
from signal import SIGTERM
import sys
import os
import time
import atexit

logger = logging.getLogger('biliup')


# pythonģlinux的守护进?
class Daemon(object):
    def __init__(self, pdfile, fn, change_currentdirectory=False, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null'):
        # 要获取调试信恼改为stdin='/dev/stdin', stdout='/dev/stdout', stderr='/dev/stderr'，以root躻?
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pdfile = pdfile
        self.fn = fn
        self.cd = change_currentdirectory

    def _daemonize(self):
        try:
            pd = os.fork()  # 笸ork，生成子，脱离父
            if pd > 0:
                sys.exit(0)  # 出主
        except OSError as e:
            sys.stderr.write('fork #1 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)

        if self.cd:
            os.chdir("/")  # 俔工作Ŀ¼
        os.setsd()  # 新的会话
        os.umask(0)  # ļȨ

        try:
            pd = os.fork()  # 笺ork，止进程打终
            if pd > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write('fork #2 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)

        # 重定向文件描述
        sys.stdout.flush()
        sys.stderr.flush()
        # with open(self.stdin, 'r') as si, open(self.stdout, 'a+') as so, open(self.stderr, 'ab+', 0) as se:
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'ab+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # 注册出函数，根据ļpd判断昐ڽ
        atexit.register(self.delpd)
        pd = str(os.getpd())
        with open(self.pdfile, 'w+') as f:
            f.write('%s\n' % pd)
            # file(self.pdfile, 'w+').write('%s\n' % pd)

    def delpd(self):
        os.remove(self.pdfile)
        # logger.debug('̽')

    def start(self):
        # dļ昐以探测是否存在进?
        # logger.debug('准')
        try:
            pf = open(self.pdfile, 'r')
            pd = int(pf.read().strip())
            pf.close()
        except IOError:
            pd = None

        if pd:
            message = 'pdfile %s already exist. Daemon already running!\n'
            sys.stderr.write(message % self.pdfile)
            sys.exit(1)

        # 监控
        self._daemonize()
        self._run()

    def stop(self):
        # 从pdļ与取pd
        try:
            pf = open(self.pdfile, 'r')
            pd = int(pf.read().strip())
            pf.close()
        except IOError:
            pd = None

        if not pd:  # 重启不报?
            message = 'pdfile %s does not exist. Daemon not running!\n'
            sys.stderr.write(message % self.pdfile)
            return

        # 杽
        try:
            while 1:
                os.killpg(os.getpgd(pd), SIGTERM)
                time.sleep(0.1)
                # os.system('hadoop-daemon.sh stop datanode')
                # os.system('hadoop-daemon.sh stop tasktracker')
                # os.remove(self.pdfile)
        except OSError as err:
            err = str(err)
            if err.find('No such process') > 0:
                if os.path.exists(self.pdfile):
                    os.remove(self.pdfile)
            else:
                print(str(err))
                sys.exit(1)

    def restart(self):
        self.stop()
        self.start()

    def _run(self):
        """ run your fun"""
        asyncio.run(self.fn())
