#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename: __timeQueue.py

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
@brief: 璇锋眰鍝嶅簲鎶ユ枃鍜岃秴鏃堕槦鍒?
'''

import struct
import threading
import time

from .__logger import tarsLogger
from .__packet import RequestPacket
from .__packet import ResponsePacket
from .__tars import TarsInputStream
from .__tars import TarsOutputStream
from .__util import (NewLock, LockGuard)


class ReqMessage:
    '''
    @brief: 璇锋眰鍝嶅簲鎶ユ枃锛屼繚瀛樹竴涓姹傚搷搴旀墍闇€瑕佺殑鏁版嵁
    '''
    SYNC_CALL = 1
    ASYNC_CALL = 2
    ONE_WAY = 3

    def __init__(self):
        self.type = ReqMessage.SYNC_CALL
        self.servant = None
        self.lock = None
        self.adapter = None
        self.request = None
        self.response = None
        self.callback = None
        self.begtime = None
        self.endtime = None
        self.isHash = False
        self.isConHash = False
        self.hashCode = 0

    def packReq(self):
        '''
        @brief: 搴忓垪鍖栬姹傛姤鏂?
        @return: 搴忓垪鍖栧悗鐨勮姹傛姤鏂?
        @rtype: str
        '''
        if not self.request:
            return ''
        oos = TarsOutputStream()
        RequestPacket.writeTo(oos, self.request)
        reqpkt = oos.getBuffer()
        plen = len(reqpkt) + 4
        reqpkt = struct.pack('!i', plen) + reqpkt
        return reqpkt

    @staticmethod
    def unpackRspList(buf):
        '''
        @brief: 瑙ｇ爜鍝嶅簲鎶ユ枃
        @param buf: 澶氫釜搴忓垪鍖栧悗鐨勫搷搴旀姤鏂囨暟鎹?
        @type buf: str
        @return: 瑙ｇ爜鍑烘潵鐨勫搷搴旀姤鏂囧拰瑙ｇ爜鐨刡uffer闀垮害
        @rtype: rsplist: 瑁呮湁ResponsePacket鐨刲ist
                unpacklen: int
        '''
        rsplist = []
        if not buf:
            return rsplist

        unpacklen = 0
        buf = buffer(buf)
        while True:
            if len(buf) - unpacklen < 4:
                break
            packsize = buf[unpacklen: unpacklen+4]
            packsize, = struct.unpack_from('!i', packsize)
            if len(buf) < unpacklen + packsize:
                break

            ios = TarsInputStream(buf[unpacklen+4: unpacklen+packsize])
            rsp = ResponsePacket.readFrom(ios)
            rsplist.append(rsp)
            unpacklen += packsize

        return rsplist, unpacklen

# 瓒呮椂闃熷垪锛屽姞閿侊紝绾跨▼瀹夊叏


class TimeoutQueue:
    '''
    @brief: 瓒呮椂闃熷垪锛屽姞閿侊紝绾跨▼瀹夊叏
            鍙互鍍忛槦鍒椾竴鏍稦IFO锛屼篃鍙互鍍忓瓧鍏镐竴鏍锋寜key鍙杋tem
    @todo: 闄愬埗闃熷垪闀垮害
    '''

    def __init__(self, timeout=3):
        self.__uniqId = 0
        # self.__lock = threading.Lock()
        self.__lock = NewLock()
        self.__data = {}
        self.__queue = []
        self.__timeout = timeout

    def getTimeout(self):
        '''
        @brief: 鑾峰彇瓒呮椂鏃堕棿锛屽崟浣嶄负s
        @return: 瓒呮椂鏃堕棿
        @rtype: float
        '''
        return self.__timeout

    def setTimeout(self, timeout):
        '''
        @brief: 璁剧疆瓒呮椂鏃堕棿锛屽崟浣嶄负s
        @param timeout: 瓒呮椂鏃堕棿
        @type timeout: float
        @return: None
        @rtype: None
        '''
        self.__timeout = timeout

    def size(self):
        '''
        @brief: 鑾峰彇闃熷垪闀垮害
        @return: 闃熷垪闀垮害
        @rtype: int
        '''
        # self.__lock.acquire()
        lock = LockGuard(self.__lock)
        ret = len(self.__data)
        # self.__lock.release()
        return ret

    def generateId(self):
        '''
        @brief: 鐢熸垚鍞竴id锛? < id < 2 ** 32
        @return: id
        @rtype: int
        '''
        # self.__lock.acquire()
        lock = LockGuard(self.__lock)
        ret = self.__uniqId
        ret = (ret + 1) % 0x7FFFFFFF
        while ret <= 0:
            ret = (ret + 1) % 0x7FFFFFFF
        self.__uniqId = ret
        # self.__lock.release()
        return ret

    def pop(self, uniqId=0, erase=True):
        '''
        @brief: 寮瑰嚭item
        @param uniqId: item鐨刬d锛屽鏋滀负0锛屾寜FIFO寮瑰嚭
        @type uniqId: int
        @param erase: 寮瑰嚭鍚庢槸鍚︿粠瀛楀吀閲屽垹闄tem
        @type erase: bool
        @return: item
        @rtype: any type
        '''
        ret = None

        # self.__lock.acquire()
        lock = LockGuard(self.__lock)

        if not uniqId:
            if len(self.__queue):
                uniqId = self.__queue.pop(0)
        if uniqId:
            if erase:
                ret = self.__data.pop(uniqId, None)
            else:
                ret = self.__data.get(uniqId, None)

        # self.__lock.release()

        return ret[0] if ret else None

    def push(self, item, uniqId):
        '''
        @brief: 鏁版嵁鍏ラ槦鍒楋紝濡傛灉闃熷垪宸茬粡鏈変簡uniqId锛屾彃鍏ュけ璐?
        @param item: 鎻掑叆鐨勬暟鎹?
        @type item: any type
        @return: 鎻掑叆鏄惁鎴愬姛
        @rtype: bool
        '''
        begtime = time.time()
        ret = True
        # self.__lock.acquire()
        lock = LockGuard(self.__lock)

        if uniqId in self.__data:
            ret = False
        else:
            self.__data[uniqId] = [item, begtime]
            self.__queue.append(uniqId)
        # self.__lock.release()
        return ret

    def peek(self, uniqId):
        '''
        @brief: 鏍规嵁uniqId鑾峰彇item锛屼笉浼氬垹闄tem
        @param uniqId: item鐨刬d
        @type uniqId: int
        @return: item
        @rtype: any type
        '''
        # self.__lock.acquire()
        lock = LockGuard(self.__lock)

        ret = self.__data.get(uniqId, None)
        # self.__lock.release()
        if not ret:
            return None
        return ret[0]

    def timeout(self):
        '''
        @brief: 妫€娴嬫槸鍚︽湁item瓒呮椂锛屽鏋滄湁灏卞垹闄?
        @return: None
        @rtype: None
        '''
        endtime = time.time()
        # self.__lock.acquire()
        lock = LockGuard(self.__lock)

        # 澶勭悊寮傚父鎯呭喌锛岄槻姝㈡閿?
        try:
            new_data = {}
            for uniqId, item in self.__data.items():
                if endtime - item[1] < self.__timeout:
                    new_data[uniqId] = item
                else:
                    tarsLogger.debug(
                        'TimeoutQueue:timeout remove id : %d' % uniqId)
            self.__data = new_data
        finally:
            # self.__lock.release()
            pass


class QueueTimeout(threading.Thread):
    """
    瓒呮椂绾跨▼锛屽畾鏃惰Е鍙戣秴鏃朵簨浠?
    """

    def __init__(self, timeout=0.1):
        # threading.Thread.__init__(self)
        tarsLogger.debug('QueueTimeout:__init__')
        super(QueueTimeout, self).__init__()
        self.timeout = timeout
        self.__terminate = False
        self.__handler = None
        self.__lock = threading.Condition()

    def terminate(self):
        tarsLogger.debug('QueueTimeout:terminate')
        self.__terminate = True
        self.__lock.acquire()
        self.__lock.notifyAll()
        self.__lock.release()

    def setHandler(self, handler):
        self.__handler = handler

    def run(self):
        while not self.__terminate:
            try:
                self.__lock.acquire()
                self.__lock.wait(self.timeout)
                self.__lock.release()
                if self.__terminate:
                    break
                self.__handler()
            except Exception as msg:
                tarsLogger.error('QueueTimeout:run exception : %s', msg)

        tarsLogger.debug('QueueTimeout:run finished')


if __name__ == '__main__':
    pass
