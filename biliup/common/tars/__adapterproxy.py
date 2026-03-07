#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename: __adapterproxymanager.py_compiler

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
@brief: 灏唕pc閮ㄥ垎涓殑adapterproxymanager鎶界鍑烘潵锛屽疄鐜颁笉鍚岀殑璐熻浇鍧囪　
'''

import os
import random
import select
import socket
import time
from enum import Enum

from . import exception
# 鍥犱负寰幆import鐨勯棶棰樺彧鑳芥斁杩欓噷锛屼笉鑳芥斁鏂囦欢寮€濮嬪
from .QueryF import QueryFProxy
from .QueryF import QueryFPrxCallback
from .__TimeoutQueue import ReqMessage
from .__logger import tarsLogger
from .__trans import EndPointInfo
from .__trans import TcpTransceiver
from .__util import (LockGuard, NewLock, ConsistentHashNew)
from .exception import TarsException


class AdapterProxy:
    '''
    @brief: 姣忎竴涓狝dapter绠＄悊涓€涓湇鍔＄绔彛鐨勮繛鎺ワ紝鏁版嵁鏀跺彂
    '''

    def __init__(self):
        tarsLogger.debug('AdapterProxy:__init__')
        self.__closeTrans = False
        self.__trans = None
        self.__object = None
        self.__reactor = None
        self.__lock = None
        self.__asyncProc = None
        self.__activeStateInReg = True

    @property
    def activatestateinreg(self):
        return self.__activeStateInReg

    @activatestateinreg.setter
    def activatestateinreg(self, value):
        self.__activeStateInReg = value

    def __del__(self):
        tarsLogger.debug('AdapterProxy:__del__')

    def initialize(self, endPointInfo, objectProxy, reactor, asyncProc):
        '''
        @brief: 鍒濆鍖?
        @param endPointInfo: 杩炴帴瀵圭淇℃伅
        @type endPointInfo: EndPointInfo
        @type objectProxy: ObjectProxy
        @type reactor: FDReactor
        @type asyncProc: AsyncProcThread
        '''
        tarsLogger.debug('AdapterProxy:initialize')
        self.__closeTrans = False
        self.__trans = TcpTransceiver(endPointInfo)
        self.__object = objectProxy
        self.__reactor = reactor
        # self.__lock = threading.Lock()
        self.__lock = NewLock()
        self.__asyncProc = asyncProc

    def terminate(self):
        '''
        @brief: 鍏抽棴
        '''
        tarsLogger.debug('AdapterProxy:terminate')
        self.setCloseTrans(True)

    def trans(self):
        '''
        @brief: 鑾峰彇浼犺緭绫?
        @return: 璐熻矗缃戠粶浼犺緭鐨則rans
        @rtype: Transceiver
        '''
        return self.__trans

    def invoke(self, reqmsg):
        '''
        @brief: 杩滅▼杩囩▼璋冪敤澶勭悊鏂规硶
        @param reqmsg: 璇锋眰鍝嶅簲鎶ユ枃
        @type reqmsg: ReqMessage
        @return: 閿欒鐮侊細0琛ㄧず鎴愬姛锛?1琛ㄧず杩炴帴澶辫触
        @rtype: int
        '''
        tarsLogger.debug('AdapterProxy:invoke')
        assert(self.__trans)

        if (not self.__trans.hasConnected() and
                not self.__trans.isConnecting):
            # -1琛ㄧず杩炴帴澶辫触
            return -1

        reqmsg.request.iRequestId = self.__object.getTimeoutQueue().generateId()
        self.__object.getTimeoutQueue().push(reqmsg, reqmsg.request.iRequestId)

        self.__reactor.notify(self)

        return 0

    def finished(self, rsp):
        '''
        @brief: 杩滅▼杩囩▼璋冪敤杩斿洖澶勭悊
        @param rsp: 鍝嶅簲鎶ユ枃
        @type rsp: ResponsePacket
        @return: 鍑芥暟鏄惁鎵ц鎴愬姛
        @rtype: bool
        '''
        tarsLogger.debug('AdapterProxy:finished')
        reqmsg = self.__object.getTimeoutQueue().pop(rsp.iRequestId)
        if not reqmsg:
            tarsLogger.error(
                'finished, can not get ReqMessage, may be timeout, id: %d',
                rsp.iRequestId)
            return False

        reqmsg.response = rsp
        if reqmsg.type == ReqMessage.SYNC_CALL:
            return reqmsg.servant._finished(reqmsg)
        elif reqmsg.callback:
            self.__asyncProc.put(reqmsg)
            return True

        tarsLogger.error('finished, adapter proxy finish fail, id: %d, ret: %d',
                         rsp.iRequestId, rsp.iRet)
        return False

    # 妫€娴嬭繛鎺ユ槸鍚﹀け璐ワ紝澶辨晥鏃堕噸杩?
    def checkActive(self, forceConnect=False):
        '''
        @brief: 妫€娴嬭繛鎺ユ槸鍚﹀け鏁?
        @param forceConnect: 鏄惁寮哄埗鍙戣捣杩炴帴锛屼负true鏃朵笉瀵圭姸鎬佽繘琛屽垽鏂氨鍙戣捣杩炴帴
        @type forceConnect: bool
        @return: 杩炴帴鏄惁鏈夋晥
        @rtype: bool
        '''
        tarsLogger.debug('AdapterProxy:checkActive')
        # self.__lock.acquire()
        lock = LockGuard(self.__lock)
        tarsLogger.info('checkActive, %s, forceConnect: %s',
                        self.__trans.getEndPointInfo(), forceConnect)

        if not self.__trans.isConnecting() and not self.__trans.hasConnected():
            self.doReconnect()

        # self.__lock.release()
        return self.__trans.isConnecting() or self.__trans.hasConnected()

    def doReconnect(self):
        '''
        @brief: 閲嶆柊鍙戣捣杩炴帴
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('AdapterProxy:doReconnect')
        assert(self.__trans)

        self.__trans.reInit()
        tarsLogger.info('doReconnect, connect: %s, fd:%d',
                        self.__trans.getEndPointInfo(),
                        self.__trans.getFd())

        self.__reactor.registerAdapter(self, select.EPOLLIN | select.EPOLLOUT)

    def sendRequest(self):
        '''
        @brief: 鎶婇槦鍒椾腑鐨勮姹傛斁鍒癟ransceiver鐨勫彂閫佺紦瀛橀噷
        @return: 鏀惧叆缂撳瓨鐨勬暟鎹暱搴?
        @rtype: int
        '''
        tarsLogger.debug('AdapterProxy:sendRequest')
        if not self.__trans.hasConnected():
            return False

        reqmsg = self.__object.popRequest()
        blen = 0
        while reqmsg:
            reqmsg.adapter = self
            buf = reqmsg.packReq()
            self.__trans.writeToSendBuf(buf)
            tarsLogger.info('sendRequest, id: %d, len: %d',
                            reqmsg.request.iRequestId, len(buf))
            blen += len(buf)
            # 鍚堝苟涓€娆″彂閫佺殑鍖?鏈€澶у悎骞惰嚦8k 鎻愰珮寮傛鏃跺鎴风鏁堢巼?
            if (self.__trans.getEndPointInfo().getConnType() == EndPointInfo.SOCK_UDP
                    or blen > 8192):
                break
            reqmsg = self.__object.popRequest()

        return blen

    def finishConnect(self):
        '''
        @brief: 浣跨敤鐨勯潪闃诲socket杩炴帴涓嶈兘绔嬪埢鍒ゆ柇鏄惁杩炴帴鎴愬姛锛?
                鍦╡poll鍝嶅簲鍚庤皟鐢ㄦ鍑芥暟澶勭悊connect缁撴潫鍚庣殑鎿嶄綔
        @return: 鏄惁杩炴帴鎴愬姛
        @rtype: bool
        '''
        tarsLogger.debug('AdapterProxy:finishConnect')
        success = True
        errmsg = ''
        try:
            ret = self.__trans.getSock().getsockopt(
                socket.SOL_SOCKET, socket.SO_ERROR)
            if ret:
                success = False
                errmsg = os.strerror(ret)
        except Exception as msg:
            errmsg = msg
            success = False

        if not success:
            self.__reactor.unregisterAdapter(
                self, socket.EPOLLIN | socket.EPOLLOUT)
            self.__trans.close()
            self.__trans.setConnFailed()
            tarsLogger.error(
                'AdapterProxy finishConnect, exception: %s, error: %s',
                self.__trans.getEndPointInfo(), errmsg)
            return False
        self.__trans.setConnected()
        self.__reactor.notify(self)
        tarsLogger.info('AdapterProxy finishConnect, connect %s success',
                        self.__trans.getEndPointInfo())
        return True

    def finishInvoke(self, isTimeout):
        pass

    # 寮瑰嚭璇锋眰鎶ユ枃
    def popRequest(self):
        pass

    def shouldCloseTrans(self):
        '''
        @brief: 鏄惁璁剧疆鍏抽棴杩炴帴
        @return: 鍏抽棴杩炴帴鐨刦lag鐨勫€?
        @rtype: bool
        '''
        return self.__closeTrans

    def setCloseTrans(self, closeTrans):
        '''
        @brief: 璁剧疆鍏抽棴杩炴帴flag鐨勫€?
        @param closeTrans: 鏄惁鍏抽棴杩炴帴
        @type closeTrans: bool
        @return: None
        @rtype: None
        '''
        self.__closeTrans = closeTrans


class QueryRegisterCallback(QueryFPrxCallback):
    def __init__(self, adpManager):
        self.__adpManager = adpManager
        super(QueryRegisterCallback, self).__init__()
        # QueryFPrxCallback.__init__(self)

    def callback_findObjectById4All(self, ret, activeEp, inactiveEp):
        eplist = [EndPointInfo(x.host, x.port, x.timeout, x.weight, x.weightType)
                  for x in activeEp if ret == 0 and x.istcp]
        ieplist = [EndPointInfo(x.host, x.port, x.timeout, x.weight, x.weightType)
                   for x in inactiveEp if ret == 0 and x.istcp]
        self.__adpManager.setEndpoints(eplist, ieplist)

    def callback_findObjectById4All_exception(self, ret):
        tarsLogger.error('callback_findObjectById4All_exception ret: %d', ret)


class EndpointWeightType(Enum):
    E_LOOP = 0
    E_STATIC_WEIGHT = 1


class AdapterProxyManager:
    '''
    @brief: 绠＄悊Adapter
    '''

    def __init__(self):
        tarsLogger.debug('AdapterProxyManager:__init__')
        self.__comm = None
        self.__object = None
        # __adps鐨刱ey=str(EndPointInfo) value=[EndPointInfo, AdapterProxy, cnt]
        # cnt鏄闂鏁?
        self.__adps = {}
        self.__iadps = {}
        self.__newLock = None
        self.__isDirectProxy = True
        self.__lastFreshTime = 0
        self.__queryRegisterCallback = QueryRegisterCallback(self)
        self.__regAdapterProxyDict = {}
        self.__lastConHashPrxList = []
        self.__consistentHashWeight = None
        self.__weightType = EndpointWeightType.E_LOOP
        self.__update = True
        self.__lastWeightedProxyData = {}

    def initialize(self, comm, objectProxy, eplist):
        '''
        @brief: 鍒濆鍖?
        '''
        tarsLogger.debug('AdapterProxyManager:initialize')
        self.__comm = comm
        self.__object = objectProxy
        self.__newLock = NewLock()

        self.__isDirectProxy = len(eplist) > 0
        if self.__isDirectProxy:
            self.setEndpoints(eplist, {})
        else:
            self.refreshEndpoints()

    def terminate(self):
        '''
        @brief: 閲婃斁璧勬簮
        '''
        tarsLogger.debug('AdapterProxyManager:terminate')
        # self.__lock.acquire()
        lock = LockGuard(self.__newLock)
        for ep, epinfo in self.__adps.items():
            epinfo[1].terminate()
        self.__adps = {}
        self.__lock.release()

    def refreshEndpoints(self):
        '''
        @brief: 鍒锋柊鏈嶅姟鍣ㄥ垪琛?
        @return: 鏂扮殑鏈嶅姟鍒楄〃
        @rtype: EndPointInfo鍒楄〃
        '''
        tarsLogger.debug('AdapterProxyManager:refreshEndpoints')
        if self.__isDirectProxy:
            return

        interval = self.__comm.getProperty(
            'refresh-endpoint-interval', float) / 1000
        locator = self.__comm.getProperty('locator')

        if '@' not in locator:
            raise exception.TarsRegistryException(
                'locator is not valid: ' + locator)

        now = time.time()
        last = self.__lastFreshTime
        epSize = len(self.__adps)
        if last + interval < now or (epSize <= 0 and last + 2 < now):
            queryFPrx = self.__comm.stringToProxy(QueryFProxy, locator)
            # 棣栨璁块棶鏄悓姝ヨ皟鐢紝涔嬪悗璁块棶鏄紓姝ヨ皟鐢?
            if epSize == 0 or last == 0:
                ret, activeEps, inactiveEps = (
                    queryFPrx.findObjectById4All(self.__object.name()))
                # 鐩墠鍙敮鎸乀CP
                eplist = [EndPointInfo(x.host, x.port, x.timeout, x.weight, x.weightType)
                          for x in activeEps if ret == 0 and x.istcp]
                ieplist = [EndPointInfo(x.host, x.port, x.timeout, x.weight, x.weightType)
                           for x in inactiveEps if ret == 0 and x.istcp]
                self.setEndpoints(eplist, ieplist)
            else:
                queryFPrx.async_findObjectById4All(self.__queryRegisterCallback,
                                                   self.__object.name())
            self.__lastFreshTime = now

    def getEndpoints(self):
        '''
        @brief: 鑾峰彇鍙敤鏈嶅姟鍒楄〃 濡傛灉鍚敤鍒嗙粍,鍙繑鍥炲悓鍒嗙粍鐨勬湇鍔＄ip
        @return: 鑾峰彇鑺傜偣鍒楄〃
        @rtype: EndPointInfo鍒楄〃
        '''
        tarsLogger.debug('AdapterProxyManager:getEndpoints')
        # self.__lock.acquire()
        lock = LockGuard(self.__newLock)
        ret = [x[1][0] for x in list(self.__adps.items())]
        # self.__lock.release()

        return ret

    def setEndpoints(self, eplist, ieplist):
        '''
        @brief: 璁剧疆鏈嶅姟绔俊鎭?
        @para eplist: 娲昏穬鐨勮璋冭妭鐐瑰垪琛?
        @para ieplist: 涓嶆椿璺冪殑琚皟鑺傜偣鍒楄〃
        '''
        tarsLogger.debug('AdapterProxyManager:setEndpoints')
        adps = {}
        iadps = {}
        comm = self.__comm
        isNeedNotify = False
        # self.__lock.acquire()
        lock = LockGuard(self.__newLock)
        isStartStatic = True

        for ep in eplist:
            if ep.getWeightType() == 0:
                isStartStatic = False
            epstr = str(ep)
            if epstr in self.__adps:
                adps[epstr] = self.__adps[epstr]
                continue
            isNeedNotify = True
            self.__update = True
            adapter = AdapterProxy()
            adapter.initialize(ep, self.__object,
                               comm.getReactor(), comm.getAsyncProc())
            adapter.activatestateinreg = True
            adps[epstr] = [ep, adapter, 0]
        self.__adps, adps = adps, self.__adps

        for iep in ieplist:
            iepstr = str(iep)
            if iepstr in self.__iadps:
                iadps[iepstr] = self.__iadps[iepstr]
                continue
            isNeedNotify = True
            adapter = AdapterProxy()
            adapter.initialize(iep, self.__object,
                               comm.getReactor(), comm.getAsyncProc())
            adapter.activatestateinreg = False
            iadps[iepstr] = [iep, adapter, 0]
        self.__iadps, iadps = iadps, self.__iadps

        if isStartStatic:
            self.__weightType = EndpointWeightType.E_STATIC_WEIGHT
        else:
            self.__weightType = EndpointWeightType.E_LOOP

        # self.__lock.release()
        if isNeedNotify:
            self.__notifyEndpoints(self.__adps, self.__iadps)
        # 鍏抽棴宸茬粡澶辨晥鐨勮繛鎺?
        for ep in adps:
            if ep not in self.__adps:
                adps[ep][1].terminate()

    def __notifyEndpoints(self, actives, inactives):
        # self.__lock.acquire()
        lock = LockGuard(self.__newLock)
        self.__regAdapterProxyDict.clear()
        self.__regAdapterProxyDict.update(actives)
        self.__regAdapterProxyDict.update(inactives)
        # self.__lock.release()

    def __getNextValidProxy(self):
        '''
        @brief: 鍒锋柊鏈湴缂撳瓨鍒楄〃锛屽鏋滄湇鍔′笅绾夸簡锛岃姹傚垹闄ゆ湰鍦扮紦瀛?
        @return:
        @rtype: EndPointInfo鍒楄〃
        @todo: 浼樺寲璐熻浇鍧囪　绠楁硶
        '''
        tarsLogger.debug('AdapterProxyManager:getNextValidProxy')
        lock = LockGuard(self.__newLock)
        if len(self.__adps) == 0:
            raise TarsException("the activate adapter proxy is empty")

        sortedActivateAdp = sorted(
            list(self.__adps.items()), key=lambda item: item[1][2])
        # self.refreshEndpoints()
        # self.__lock.acquire()
        sortedActivateAdpSize = len(sortedActivateAdp)

        while sortedActivateAdpSize != 0:
            if sortedActivateAdp[0][1][1].checkActive():
                self.__adps[sortedActivateAdp[0][0]][2] += 1
                # 杩斿洖鐨勬槸 adapterProxy
                return self.__adps[sortedActivateAdp[0][0]][1]
            sortedActivateAdp.pop(0)
            sortedActivateAdpSize -= 1
        # 闅忔満閲嶈繛涓€涓彲鐢ㄨ妭鐐?
        adpPrx = list(self.__adps.items())[random.randint(
            0, len(self.__adps))][1][1]
        adpPrx.checkActive()
        return None
        # self.__lock.release()

    def __getHashProxy(self, reqmsg):
        if self.__weightType == EndpointWeightType.E_LOOP:
            if reqmsg.isConHash:
                return self.__getConHashProxyForNormal(reqmsg.hashCode)
            else:
                return self.__getHashProxyForNormal(reqmsg.hashCode)
        else:
            if reqmsg.isConHash:
                return self.__getConHashProxyForWeight(reqmsg.hashCode)
            else:
                return self.__getHashProxyForWeight(reqmsg.hashCode)

    def __getHashProxyForNormal(self, hashCode):
        tarsLogger.debug('AdapterProxyManager:getHashProxyForNormal')
        # self.__lock.acquire()
        lock = LockGuard(self.__newLock)
        regAdapterProxyList = sorted(
            list(self.__regAdapterProxyDict.items()), key=lambda item: item[0])

        allPrxSize = len(regAdapterProxyList)
        if allPrxSize == 0:
            raise TarsException("the adapter proxy is empty")
        hashNum = hashCode % allPrxSize

        if regAdapterProxyList[hashNum][1][1].activatestateinreg and regAdapterProxyList[hashNum][1][1].checkActive():
            epstr = regAdapterProxyList[hashNum][0]
            self.__regAdapterProxyDict[epstr][2] += 1
            if epstr in self.__adps:
                self.__adps[epstr][2] += 1
            elif epstr in self.__iadps:
                self.__iadps[epstr][2] += 1
            return self.__regAdapterProxyDict[epstr][1]
        else:
            if len(self.__adps) == 0:
                raise TarsException("the activate adapter proxy is empty")
            activeProxyList = list(self.__adps.items())
            actPrxSize = len(activeProxyList)
            while actPrxSize != 0:
                hashNum = hashCode % actPrxSize
                if activeProxyList[hashNum][1][1].checkActive():
                    self.__adps[activeProxyList[hashNum][0]][2] += 1
                    return self.__adps[activeProxyList[hashNum][0]][1]
                activeProxyList.pop(hashNum)
                actPrxSize -= 1
            # 闅忔満閲嶈繛涓€涓彲鐢ㄨ妭鐐?
            adpPrx = list(self.__adps.items())[random.randint(
                0, len(self.__adps))][1][1]
            adpPrx.checkActive()
            return None

    def __getConHashProxyForNormal(self, hashCode):
        tarsLogger.debug('AdapterProxyManager:getConHashProxyForNormal')
        lock = LockGuard(self.__newLock)
        if len(self.__regAdapterProxyDict) == 0:
            raise TarsException("the adapter proxy is empty")
        if self.__consistentHashWeight is None or self.__checkConHashChange(self.__lastConHashPrxList):
            self.__updateConHashProxyWeighted()

        if len(self.__consistentHashWeight.nodes) > 0:
            conHashIndex = self.__consistentHashWeight.getNode(hashCode)
            if conHashIndex in self.__regAdapterProxyDict and self.__regAdapterProxyDict[conHashIndex][1].activatestateinreg and self.__regAdapterProxyDict[conHashIndex][1].checkActive():
                self.__regAdapterProxyDict[conHashIndex][2] += 1
                if conHashIndex in self.__adps:
                    self.__adps[conHashIndex][2] += 1
                elif conHashIndex in self.__iadps:
                    self.__iadps[conHashIndex][2] += 1
                return self.__regAdapterProxyDict[conHashIndex][1]
            else:
                if len(self.__adps) == 0:
                    raise TarsException("the activate adapter proxy is empty")
                activeProxyList = list(self.__adps.items())
                actPrxSize = len(activeProxyList)
                while actPrxSize != 0:
                    hashNum = hashCode % actPrxSize
                    if activeProxyList[hashNum][1][1].checkActive():
                        self.__adps[activeProxyList[hashNum][0]][2] += 1
                        return self.__adps[activeProxyList[hashNum][0]][1]
                    activeProxyList.pop(hashNum)
                    actPrxSize -= 1
                # 闅忔満閲嶈繛涓€涓彲鐢ㄨ妭鐐?
                adpPrx = list(self.__adps.items())[random.randint(
                    0, len(self.__adps))][1][1]
                adpPrx.checkActive()
                return None
            pass
        else:
            return self.__getHashProxyForNormal(hashCode)

    def __getHashProxyForWeight(self, hashCode):
        return None
        pass

    def __getConHashProxyForWeight(self, hashCode):
        return None
        pass

    def __checkConHashChange(self, lastConHashPrxList):
        tarsLogger.debug('AdapterProxyManager:checkConHashChange')
        lock = LockGuard(self.__newLock)
        if len(lastConHashPrxList) != len(self.__regAdapterProxyDict):
            return True
        regAdapterProxyList = sorted(
            list(self.__regAdapterProxyDict.items()), key=lambda item: item[0])
        regAdapterProxyListSize = len(regAdapterProxyList)
        for index in range(regAdapterProxyListSize):
            if cmp(lastConHashPrxList[index][0], regAdapterProxyList[index][0]) != 0:
                return True
        return False

    def __updateConHashProxyWeighted(self):
        tarsLogger.debug('AdapterProxyManager:updateConHashProxyWeighted')
        lock = LockGuard(self.__newLock)
        if len(self.__regAdapterProxyDict) == 0:
            raise TarsException("the adapter proxy is empty")
        self.__lastConHashPrxList = sorted(
            list(self.__regAdapterProxyDict.items()), key=lambda item: item[0])
        nodes = []
        for var in self.__lastConHashPrxList:
            nodes.append(var[0])
        if self.__consistentHashWeight is None:
            self.__consistentHashWeight = ConsistentHashNew(nodes)
        else:
            theOldActiveNodes = [
                var for var in nodes if var in self.__consistentHashWeight.nodes]

            theOldInactiveNodes = [
                var for var in self.__consistentHashWeight.nodes if var not in theOldActiveNodes]
            for var in theOldInactiveNodes:
                self.__consistentHashWeight.removeNode(var)

            theNewActiveNodes = [
                var for var in nodes if var not in theOldActiveNodes]
            for var in theNewActiveNodes:
                self.__consistentHashWeight.addNode(var)

            self.__consistentHashWeight.nodes = nodes
        pass

    def __getWeightedProxy(self):
        tarsLogger.debug('AdapterProxyManager:getWeightedProxy')
        lock = LockGuard(self.__newLock)
        if len(self.__adps) == 0:
            raise TarsException("the activate adapter proxy is empty")

        if self.__update is True:
            self.__lastWeightedProxyData.clear()
            weightedProxyData = {}
            minWeight = (list(self.__adps.items())[0][1][0]).getWeight()
            for item in list(self.__adps.items()):
                weight = (item[1][0].getWeight())
                weightedProxyData[item[0]] = (weight)
                if minWeight > weight:
                    minWeight = weight

            if minWeight <= 0:
                addWeight = -minWeight + 1
                for item in list(weightedProxyData.items()):
                    item[1] += addWeight

            self.__update = False
            self.__lastWeightedProxyData = weightedProxyData

        weightedProxyData = self.__lastWeightedProxyData
        while len(weightedProxyData) > 0:
            total = sum(weightedProxyData.values())
            rand = random.randint(1, total)
            temp = 0
            for item in list(weightedProxyData.items()):
                temp += item[1]
                if rand <= temp:
                    if self.__adps[item[0]][1].checkActive():
                        self.__adps[item[0]][2] += 1
                        return self.__adps[item[0]][1]
                    else:
                        weightedProxyData.pop(item[0])
                        break
        # 娌℃湁涓€涓椿璺冪殑鑺傜偣
        # 闅忔満閲嶈繛涓€涓彲鐢ㄨ妭鐐?
        adpPrx = list(self.__adps.items())[random.randint(
            0, len(self.__adps))][1][1]
        adpPrx.checkActive()
        return None

    def selectAdapterProxy(self, reqmsg):
        '''
        @brief: 鍒锋柊鏈湴缂撳瓨鍒楄〃锛屽鏋滄湇鍔′笅绾夸簡锛岃姹傚垹闄ゆ湰鍦扮紦瀛橈紝閫氳繃涓€瀹氱畻娉曡繑鍥濧dapterProxy
        @param: reqmsg:璇锋眰鍝嶅簲鎶ユ枃
        @type reqmsg: ReqMessage
        @return:
        @rtype: EndPointInfo鍒楄〃
        @todo: 浼樺寲璐熻浇鍧囪　绠楁硶
        '''
        tarsLogger.debug('AdapterProxyManager:selectAdapterProxy')
        self.refreshEndpoints()
        if reqmsg.isHash:
            return self.__getHashProxy(reqmsg)
        else:
            if self.__weightType == EndpointWeightType.E_STATIC_WEIGHT:
                return self.__getWeightedProxy()
            else:
                return self.__getNextValidProxy()
