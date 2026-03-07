import asyncio
import logging
from signal import SIGTERM
import sys
import os
import time
import atexit

logger = logging.getLogger('biliup')


# python妯℃嫙linux鐨勫畧鎶よ繘绋?
class Daemon(object):
    def __init__(self, pidfile, fn, change_currentdirectory=False, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null'):
        # 闇€瑕佽幏鍙栬皟璇曚俊鎭紝鏀逛负stdin='/dev/stdin', stdout='/dev/stdout', stderr='/dev/stderr'锛屼互root韬唤运行銆?
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.fn = fn
        self.cd = change_currentdirectory

    def _daemonize(self):
        try:
            pid = os.fork()  # 绗竴娆ork锛岀敓鎴愬瓙杩涚▼锛岃劚绂荤埗杩涚▼
            if pid > 0:
                sys.exit(0)  # 閫€鍑轰富杩涚▼
        except OSError as e:
            sys.stderr.write('fork #1 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)

        if self.cd:
            os.chdir("/")  # 淇敼宸ヤ綔目录
        os.setsid()  # 设置鏂扮殑浼氳瘽杩炴帴
        os.umask(0)  # 閲嶆柊设置文件创建鏉冮檺

        try:
            pid = os.fork()  # 绗簩娆ork锛岀姝㈣繘绋嬫墦寮€缁堢
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write('fork #2 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)

        # 閲嶅畾鍚戞枃浠舵弿杩扮
        sys.stdout.flush()
        sys.stderr.flush()
        # with open(self.stdin, 'r') as si, open(self.stdout, 'a+') as so, open(self.stderr, 'ab+', 0) as se:
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'ab+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # 娉ㄥ唽閫€鍑哄嚱鏁帮紝鏍规嵁文件pid鍒ゆ柇鏄惁存在杩涚▼
        atexit.register(self.delpid)
        pid = str(os.getpid())
        with open(self.pidfile, 'w+') as f:
            f.write('%s\n' % pid)
            # file(self.pidfile, 'w+').write('%s\n' % pid)

    def delpid(self):
        os.remove(self.pidfile)
        # logger.debug('杩涚▼结束')

    def start(self):
        # 检鏌id文件鏄惁存在浠ユ帰娴嬫槸鍚﹀瓨鍦ㄨ繘绋?
        # logger.debug('鍑嗗启动杩涚▼')
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = 'pidfile %s already exist. Daemon already running!\n'
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # 启动鐩戞帶
        self._daemonize()
        self._run()

    def stop(self):
        # 浠巔id文件涓幏鍙杙id
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:  # 閲嶅惎涓嶆姤閿?
            message = 'pidfile %s does not exist. Daemon not running!\n'
            sys.stderr.write(message % self.pidfile)
            return

        # 鏉€杩涚▼
        try:
            while 1:
                os.killpg(os.getpgid(pid), SIGTERM)
                time.sleep(0.1)
                # os.system('hadoop-daemon.sh stop datanode')
                # os.system('hadoop-daemon.sh stop tasktracker')
                # os.remove(self.pidfile)
        except OSError as err:
            err = str(err)
            if err.find('No such process') > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print(str(err))
                sys.exit(1)

    def restart(self):
        self.stop()
        self.start()

    def _run(self):
        """ run your fun"""
        asyncio.run(self.fn())
