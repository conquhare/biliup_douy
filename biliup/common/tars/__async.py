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
@brief: 寮傛rpc瀹炵幇
'''

import queue
import threading

from biliup.Danmaku.tars.__logger import tarsLogger
from biliup.Danmaku.tars.__packet import ResponsePacket
from biliup.Danmaku.tars.__servantproxy import ServantProxy


class AsyncProcThread:
    '''
    @brief: 寮傛璋冪敤绾跨▼绠＄悊绫?
    '''

    def __init__(self):
        tarsLogger.debug('AsyncProcThread:__init__')
        self.__initialize = False
        self.__runners = []
        self.__queue = None
        self.__nrunner = 0
        self.__popTimeout = 0.1

    def __del__(self):
        tarsLogger.debug('AsyncProcThread:__del__')

    def initialize(self, nrunner=3):
        '''
        @brief: 浣跨敤AsyncProcThread鍓嶅繀椤诲厛璋冪敤姝ゅ嚱鏁?
        @param nrunner: 寮傛绾跨▼涓暟
        @type nrunner: int
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('AsyncProcThread:initialize')
        if self.__initialize:
            return
        self.__nrunner = nrunner
        self.__queue = queue.Queue()
        self.__initialize = True

    def terminate(self):
        '''
        @brief: 关闭鎵€鏈夊紓姝ョ嚎绋?
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('AsyncProcThread:terminate')

        for runner in self.__runners:
            runner.terminate()

        for runner in self.__runners:
            runner.join()
        self.__runners = []

    def put(self, reqmsg):
        '''
        @brief: 处理数据鍏ラ槦鍒?
        @param reqmsg: 寰呭鐞嗘暟鎹?
        @type reqmsg: ReqMessage
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('AsyncProcThread:put')
        # 寮傛璇锋眰瓒呮椂
        if not reqmsg.response:
            reqmsg.response = ResponsePacket()
            reqmsg.response.iVerson = reqmsg.request.iVerson
            reqmsg.response.cPacketType = reqmsg.request.cPacketType
            reqmsg.response.iRequestId = reqmsg.request.iRequestId
            reqmsg.response.iRet = ServantProxy.TARSASYNCCALLTIMEOUT

        self.__queue.put(reqmsg)

    def pop(self):
        '''
        @brief: 处理数据鍑洪槦鍒?
        @return: ReqMessage
        @rtype: ReqMessage
        '''
        # tarsLogger.debug('AsyncProcThread:pop')
        ret = None
        try:
            ret = self.__queue.get(True, self.__popTimeout)
        except queue.Empty:
            pass
        return ret

    def start(self):
        '''
        @brief: 启动寮傛绾跨▼
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('AsyncProcThread:start')
        for i in range(self.__nrunner):
            runner = AsyncProcThreadRunner()
            runner.initialize(self)
            runner.start()
            self.__runners.append(runner)


class AsyncProcThreadRunner(threading.Thread):
    '''
    @brief: 寮傛璋冪敤绾跨▼
    '''

    def __init__(self):
        tarsLogger.debug('AsyncProcThreadRunner:__init__')
        super(AsyncProcThreadRunner, self).__init__()
        # threading.Thread.__init__(self)
        self.__terminate = False
        self.__initialize = False
        self.__procQueue = None

    def __del__(self):
        tarsLogger.debug('AsyncProcThreadRunner:__del__')

    def initialize(self, queue):
        '''
        @brief: 浣跨敤AsyncProcThreadRunner鍓嶅繀椤昏皟鐢ㄦ鍑芥暟
        @param queue: 鏈塸op()鐨勭被锛岀敤浜庢彁鍙栧緟处理数据
        @type queue: AsyncProcThread
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('AsyncProcThreadRunner:initialize')
        self.__procQueue = queue

    def terminate(self):
        '''
        @brief: 关闭绾跨▼
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('AsyncProcThreadRunner:terminate')
        self.__terminate = True

    def run(self):
        '''
        @brief: 绾跨▼启动鍑芥暟锛屾墽琛屽紓姝ヨ皟鐢?
        '''
        tarsLogger.debug('AsyncProcThreadRunner:run')
        while not self.__terminate:
            if self.__terminate:
                break
            reqmsg = self.__procQueue.pop()
            if not reqmsg or not reqmsg.callback:
                continue

            if reqmsg.adapter:
                succ = reqmsg.response.iRet == ServantProxy.TARSSERVERSUCCESS
                reqmsg.adapter.finishInvoke(succ)

            try:
                reqmsg.callback.onDispatch(reqmsg)
            except Exception as msg:
                tarsLogger.error('AsyncProcThread excepttion: %s', msg)

        tarsLogger.debug('AsyncProcThreadRunner:run finished')


class ServantProxyCallback(object):
    '''
    @brief: 寮傛鍥炶皟瀵硅薄鍩虹被
    '''

    def __init__(self):
        tarsLogger.debug('ServantProxyCallback:__init__')

    def onDispatch(reqmsg):
        '''
        @brief: 鍒嗛厤鍝嶅簲鎶ユ枃鍒板搴旂殑鍥炶皟鍑芥暟
        @param queue: 鏈塸op()鐨勭被锛岀敤浜庢彁鍙栧緟处理数据
        @type queue: AsyncProcThread
        @return: None
        @rtype: None
        '''
        raise NotImplementedError()
