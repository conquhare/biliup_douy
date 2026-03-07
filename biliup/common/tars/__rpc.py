#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename: __rpc.py

# Tencent is pleased to support the open source community by making Tars available.
#
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
#
# Licensed under the BSD 3-Clause License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# https://opensource.org/licenses/BSD-3-Clause
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#


'''
@version: 0.01
@brief: rpc璋冪敤閫昏緫瀹炵幇
'''

import argparse
import time

from .__TimeoutQueue import QueueTimeout
from .__TimeoutQueue import TimeoutQueue
from .__adapterproxy import AdapterProxyManager
from .__async import AsyncProcThread
from .__logger import initLog
from .__logger import tarsLogger
from .__servantproxy import ServantProxy
from .__trans import EndPointInfo
from .__trans import FDReactor
from .exception import (TarsException)


class Communicator:
    '''
    @brief: 閫氳鍣紝创建鍜岀淮鎶ervantProxy銆丱bjectProxy銆丗DReactor绾跨▼鍜岃秴鏃剁嚎绋?
    '''
    default_config = {'tars':
                      {'application':
                       {'client':
                        {'async-invoke-timeout': 20000,
                         'asyncthread': 0,
                         'locator': '',
                            'loglevel': 'error',
                            'logpath': 'tars.log',
                            'logsize': 15728640,
                            'lognum': 0,
                            'refresh-endpoint-interval': 60000,
                            'sync-invoke-timeout': 5000}}}}

    def __init__(self, config={}):
        tarsLogger.debug('Communicator:__init__')
        self.__terminate = False
        self.__initialize = False
        self.__objects = {}
        self.__servants = {}
        self.__reactor = None
        self.__qTimeout = None
        self.__asyncProc = None
        self.__config = Communicator.default_config.copy()
        self.__config.update(config)
        self.initialize()

    def __del__(self):
        tarsLogger.debug('Communicator:__del__')

    def initialize(self):
        '''
        @brief: 浣跨敤閫氳鍣ㄥ墠必须鍏堣皟鐢ㄦ鍑芥暟
        '''
        tarsLogger.debug('Communicator:initialize')
        if self.__initialize:
            return
        logpath = self.getProperty('logpath')
        logsize = self.getProperty('logsize', int)
        lognum = self.getProperty('lognum', int)
        loglevel = self.getProperty('loglevel')
        initLog(logpath, logsize, lognum, loglevel)

        self.__reactor = FDReactor()
        self.__reactor.initialize()
        self.__reactor.start()

        self.__qTimeout = QueueTimeout()
        self.__qTimeout.setHandler(self.handleTimeout)
        self.__qTimeout.start()

        async_num = self.getProperty('asyncthread', int)
        self.__asyncProc = AsyncProcThread()
        self.__asyncProc.initialize(async_num)
        self.__asyncProc.start()

        self.__initialize = True

    def terminate(self):
        '''
        @brief: 涓嶅啀浣跨敤閫氳鍣ㄩ渶璋冪敤姝ゅ嚱鏁伴噴鏀捐祫婧?
        '''
        tarsLogger.debug('Communicator:terminate')

        if not self.__initialize:
            return

        self.__reactor.terminate()
        self.__qTimeout.terminate()
        self.__asyncProc.terminate()

        for objName in self.__servants:
            self.__servants[objName]._terminate()

        for objName in self.__objects:
            self.__objects[objName].terminate()

        self.__objects = {}
        self.__servants = {}
        self.__reactor = None
        self.__initialize = False

    def parseConnAddr(self, connAddr):
        '''
        @brief: 解析connAddr字符涓?
        @param connAddr: 杩炴帴鍦板潃
        @type connAddr: str
        @return: 解析缁撴灉
        @rtype: dict, key鏄痵tr锛寁al閲宯ame鏄痵tr锛?
                timeout鏄痜loat锛宔ndpoint鏄疎ndPointInfo鐨刲ist
        '''
        tarsLogger.debug('Communicator:parseConnAddr')
        connAddr = connAddr.strip()
        connInfo = {
            'name': '',
            'timeout': -1,
            'endpoint': []
        }
        if '@' not in connAddr:
            connInfo['name'] = connAddr
            return connInfo

        try:
            tks = connAddr.split('@')
            connInfo['name'] = tks[0]
            tks = tks[1].lower().split(':')
            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument('-h')
            parser.add_argument('-p')
            parser.add_argument('-t')
            for tk in tks:
                argv = tk.split()
                if argv[0] != 'tcp':
                    raise TarsException(
                        'unsupport transmission protocal : %s' % connInfo['name'])
                mes = parser.parse_args(argv[1:])
                try:
                    ip = mes.h if mes.h is not None else ''
                    port = int(mes.p) if mes.p is not None else '-1'
                    timeout = int(mes.t) if mes.t is not None else '-1'
                    connInfo['endpoint'].append(
                        EndPointInfo(ip, port, timeout))
                except Exception:
                    raise TarsException('Unrecognized option : %s' % mes)
        except TarsException:
            raise

        except Exception as exp:
            raise TarsException(exp)

        return connInfo

    def getReactor(self):
        '''
        @brief: 获取reactor
        '''
        return self.__reactor

    def getAsyncProc(self):
        '''
        @brief: 获取asyncProc
        '''
        return self.__asyncProc

    def getProperty(self, name, dt_type=str):
        '''
        @brief: 获取配置
        @param name: 配置鍚嶇О
        @type name: str
        @param dt_type: 数据类型
        @type name: type
        @return: 配置鍐呭
        @rtype: str
        '''
        try:
            ret = self.__config['tars']['application']['client'][name]
            ret = dt_type(ret)
        except:
            ret = Communicator.default_config['tars']['application']['client'][name]

        return ret

    def setProperty(self, name, value):
        '''
        @brief: 淇敼配置
        @param name: 配置鍚嶇О
        @type propertys: str
        @param value: 配置鍐呭
        @type propertys: str
        @return: 设置鏄惁成功
        @rtype: bool
        '''
        try:
            self.__config['tars']['application']['client'][name] = value
            return True
        except:
            return False

    def setPropertys(self, propertys):
        '''
        @brief: 淇敼配置
        @param propertys: 配置闆嗗悎
        @type propertys: map, key type: str, value type: str
        @return: 鏃?
        @rtype: None
        '''
        pass

    def updateConfig(self):
        '''
        @brief: 閲嶆柊设置配置
        '''

    def stringToProxy(self, servantProxy, connAddr):
        '''
        @brief: 鍒濆鍖朣ervantProxy
        @param connAddr: 鏈嶅姟鍣ㄥ湴鍧€信息
        @type connAddr: str
        @param servant: servant proxy
        @type servant: ServantProxy瀛愮被
        @return: 鏃?
        @rtype: None
        @note: 濡傛灉connAddr鐨凷ervantObj杩炴帴杩囷紝杩斿洖杩炴帴杩囩殑ServantProxy
               濡傛灉没有杩炴帴杩囷紝鐢ㄥ弬鏁皊ervant鍒濆鍖栵紝杩斿洖servant
        '''
        tarsLogger.debug('Communicator:stringToProxy')

        connInfo = self.parseConnAddr(connAddr)
        objName = connInfo['name']
        if objName in self.__servants:
            return self.__servants[objName]

        objectPrx = ObjectProxy()
        objectPrx.initialize(self, connInfo)

        servantPrx = servantProxy()
        servantPrx._initialize(self.__reactor, objectPrx)
        self.__objects[objName] = objectPrx
        self.__servants[objName] = servantPrx
        return servantPrx

    def handleTimeout(self):
        '''
        @brief: 处理瓒呮椂浜嬩欢
        @return: 鏃?
        @rtype: None
        '''
        # tarsLogger.debug('Communicator:handleTimeout')
        for obj in self.__objects.values():
            obj.handleQueueTimeout()


class ObjectProxy:
    '''
    @brief: 涓€涓猳bject name鍦ㄤ竴涓狢ommunicator閲屾有涓€涓猳bjectproxy
            绠＄悊鏀跺彂鐨勬秷鎭槦鍒?
    '''
    DEFAULT_TIMEOUT = 3.0

    def __init__(self):
        tarsLogger.debug('ObjectProxy:__init__')
        self.__name = ''
        self.__timeout = ObjectProxy.DEFAULT_TIMEOUT
        self.__comm = None
        self.__epi = None
        self.__adpmanager = None
        self.__timeoutQueue = None
        # self.__adapter = None
        self.__initialize = False

    def __del__(self):
        tarsLogger.debug('ObjectProxy:__del__')

    def initialize(self, comm, connInfo):
        '''
        @brief: 鍒濆鍖栵紝浣跨敤ObjectProxy鍓嶅繀椤昏皟鐢?
        @param comm: 閫氳鍣?
        @type comm: Communicator
        @param connInfo: 杩炴帴信息
        @type comm: dict
        @return: None
        @rtype: None
        '''
        if self.__initialize:
            return
        tarsLogger.debug('ObjectProxy:initialize')
        self.__comm = comm
        # async-invoke-timeout鏉ヨ缃槦鍒楁椂闂?
        async_timeout = self.__comm.getProperty(
            'async-invoke-timeout', float) / 1000
        self.__timeoutQueue = TimeoutQueue(async_timeout)

        self.__name = connInfo['name']

        self.__timeout = self.__comm.getProperty(
            'sync-invoke-timeout', float) / 1000

        # 閫氳繃Communicator鐨勯厤缃缃秴鏃?
        # 涓嶅啀閫氳繃杩炴帴信息鐨?t鏉ヨ缃?
        # if connInfo['timeout'] != -1:
        # self.__timeout = connInfo['timeout']
        eplist = connInfo['endpoint']

        self.__adpmanager = AdapterProxyManager()
        self.__adpmanager.initialize(comm, self, eplist)

        self.__initialize = True

    def terminate(self):
        '''
        @brief: 鍥炴敹璧勬簮锛屼笉鍐嶄娇鐢∣bjectProxy鏃惰皟鐢?
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('ObjectProxy:terminate')
        self.__timeoutQueue = None
        self.__adpmanager.terminate()
        self.__initialize = False

    def name(self):
        '''
        @brief: 获取object name
        @return: object name
        @rtype: str
        '''
        return self.__name

    # def setTimeout(self, timeout):
        # '''
        # @brief: 设置瓒呮椂
        # @param timeout: 瓒呮椂时间锛屽崟浣嶄负s
        # @type timeout: float
        # @return: None
        # @rtype: None
        # '''
        # self.__timeout = timeout
        # self.__timeoutQueue.setTimeout(timeout)

    def timeout(self):
        '''
        @brief: 获取瓒呮椂时间
        @return: 瓒呮椂时间锛屽崟浣嶄负s
        @rtype: float
        '''
        return self.__timeout

    def getTimeoutQueue(self):
        '''
        @brief: 获取瓒呮椂闃熷垪
        @return: 瓒呮椂闃熷垪
        @rtype: TimeoutQueue
        '''
        return self.__timeoutQueue

    def handleQueueTimeout(self):
        '''
        @brief: 瓒呮椂浜嬩欢鍙戠敓鏃跺鐞嗚秴鏃朵簨鍔?
        @return: None
        @rtype: None
        '''
        # tarsLogger.debug('ObjectProxy:handleQueueTimeout')
        self.__timeoutQueue.timeout()

    def invoke(self, reqmsg):
        '''
        @brief: 杩滅▼杩囩▼璋冪敤
        @param reqmsg: 璇锋眰鍝嶅簲鎶ユ枃
        @type reqmsg: ReqMessage
        @return: 错误鐮?
        @rtype:
        '''
        tarsLogger.debug('ObjectProxy:invoke, objname: %s, func: %s',
                         self.__name, reqmsg.request.sFuncName)
        # 璐熻浇鍧囪　
        # adapter = self.__adpmanager.getNextValidProxy()
        adapter = self.__adpmanager.selectAdapterProxy(reqmsg)
        if not adapter:
            tarsLogger.error("invoke %s, select adapter proxy return None",
                             self.__name)
            return -2

        adapter.checkActive(True)
        reqmsg.adapter = adapter
        return adapter.invoke(reqmsg)

    # 寮瑰嚭璇锋眰鎶ユ枃
    def popRequest(self):
        '''
        @brief: 杩斿洖娑堟伅闃熷垪閲岀殑璇锋眰鍝嶅簲鎶ユ枃锛孎IFO
                涓嶅垹闄imeoutQueue閲岀殑数据锛屽搷搴旀椂瑕佺敤
        @return: 璇锋眰鍝嶅簲鎶ユ枃
        @rtype: ReqMessage
        '''
        return self.__timeoutQueue.pop(erase=False)


if __name__ == '__main__':
    connAddr = "apptest.lightServer.lightServantObj@tcp -h 10.130.64.220 -p 10001 -t 10000"
    connAddr = 'MTT.BookMarksUnifyServer.BookMarksUnifyObj@tcp -h 172.17.149.77 -t 60000 -p 10023'
    comm = Communicator()
    comm.initialize()
    servant = ServantProxy()
    servant = comm.stringToProxy(connAddr, servant)
    print(servant.tars_timeout())
    try:
        rsp = servant.tars_invoke(
            ServantProxy.TARSNORMAL, "test", '', ServantProxy.mapcls_context(), None)
        print('Servant invoke success, request id: %d, iRet: %d' % (
            rsp.iRequestId, rsp.iRet))
    except Exception as msg:
        print(msg)
    finally:
        servant.tars_terminate()
    time.sleep(2)
    print('app closing ...')
    comm.terminate()
    time.sleep(2)
    print('cpp closed')
