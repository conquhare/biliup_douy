#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename: __servantproxy.py

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
@brief: rpc鎶界鍑簊ervantproxy
'''
import threading
import time

# from __packet import ResponsePacket
from biliup.Danmaku.tars.__TimeoutQueue import ReqMessage
from biliup.Danmaku.tars.__logger import tarsLogger
from biliup.Danmaku.tars.__packet import RequestPacket
from biliup.Danmaku.tars.__util import util
from biliup.Danmaku.tars import exception
from biliup.Danmaku.tars.exception import TarsException


class ServantProxy(object):
    '''
    @brief: 1銆佽繙绋嬪璞＄殑鏈湴浠ｇ悊
            2銆佸悓鍚峴ervant鍦ㄤ竴涓€氫俊鍣ㄤ腑鏈€澶氬彧鏈変竴涓疄渚?
            3銆侀槻姝㈠拰鐢ㄦ埛鍦═ars涓畾涔夌殑鍑芥暟鍚嶅啿绐侊紝鎺ュ彛浠ars_寮€澶?
    '''

    # 鏈嶅姟鍣ㄥ搷搴旂殑閿欒鐮?
    TARSSERVERSUCCESS = 0  # 鏈嶅姟鍣ㄧ澶勭悊鎴愬姛
    TARSSERVERDECODEERR = -1  # 鏈嶅姟鍣ㄧ瑙ｇ爜寮傚父
    TARSSERVERENCODEERR = -2  # 鏈嶅姟鍣ㄧ缂栫爜寮傚父
    TARSSERVERNOFUNCERR = -3  # 鏈嶅姟鍣ㄧ娌℃湁璇ュ嚱鏁?
    TARSSERVERNOSERVANTERR = -4  # 鏈嶅姟鍣ㄧ浜旇Servant瀵硅薄
    TARSSERVERRESETGRID = -5  # 鏈嶅姟鍣ㄧ鐏板害鐘舵€佷笉涓€鑷?
    TARSSERVERQUEUETIMEOUT = -6  # 鏈嶅姟鍣ㄩ槦鍒楄秴杩囬檺鍒?
    TARSASYNCCALLTIMEOUT = -7  # 寮傛璋冪敤瓒呮椂
    TARSPROXYCONNECTERR = -8  # proxy閾炬帴寮傚父
    TARSSERVERUNKNOWNERR = -99  # 鏈嶅姟鍣ㄧ鏈煡寮傚父

    TARSVERSION = 1
    TUPVERSION = 2
    TUPVERSION2 = 3

    TARSNORMAL = 0
    TARSONEWAY = 1

    TARSMESSAGETYPENULL = 0
    TARSMESSAGETYPEHASH = 1
    TARSMESSAGETYPEGRID = 2
    TARSMESSAGETYPEDYED = 4
    TARSMESSAGETYPESAMPLE = 8
    TARSMESSAGETYPEASYNC = 16

    mapcls_context = util.mapclass(util.string, util.string)

    def __init__(self):
        tarsLogger.debug('ServantProxy:__init__')
        self.__reactor = None
        self.__object = None
        self.__initialize = False

    def __del__(self):
        tarsLogger.debug('ServantProxy:__del__')

    def _initialize(self, reactor, obj):
        '''
        @brief: 鍒濆鍖栧嚱鏁帮紝闇€瑕佽皟鐢ㄦ墠鑳戒娇鐢⊿ervantProxy
        @param reactor: 缃戠粶绠＄悊鐨剅eactor瀹炰緥
        @type reactor: FDReactor
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('ServantProxy:_initialize')

        assert(reactor and obj)
        if self.__initialize:
            return
        self.__reactor = reactor
        self.__object = obj
        self.__initialize = True

    def _terminate(self):
        '''
        @brief: 涓嶅啀浣跨敤ServantProxy鏃惰皟鐢紝浼氶噴鏀剧浉搴旇祫婧?
        @return: None
        @rtype: None
        '''
        tarsLogger.debug('ServantProxy:_terminate')
        self.__object = None
        self.__reactor = None
        self.__initialize = False

    def tars_name(self):
        '''
        @brief: 鑾峰彇ServantProxy鐨勫悕瀛?
        @return: ServantProxy鐨勫悕瀛?
        @rtype: str
        '''
        return self.__object.name()

    def tars_timeout(self):
        '''
        @brief: 鑾峰彇瓒呮椂鏃堕棿锛屽崟浣嶆槸ms
        @return: 瓒呮椂鏃堕棿
        @rtype: int
        '''
        # 榛樿鐨勪负3S = ObjectProxy.DEFAULT_TIMEOUT
        return int(self.__timeout() * 1000)

    def tars_ping(self):
        pass

    # def tars_initialize(self):
        # pass

    # def tars_terminate(self):
        # pass

    def tars_invoke(self, cPacketType, sFuncName, sBuffer, context, status):
        '''
        @brief: TARS鍗忚鍚屾鏂规硶璋冪敤
        @param cPacketType: 璇锋眰鍖呯被鍨?
        @type cPacketType: int
        @param sFuncName: 璋冪敤鍑芥暟鍚?
        @type sFuncName: str
        @param sBuffer: 搴忓垪鍖栧悗鐨勫彂閫佸弬鏁?
        @type sBuffer: str
        @param context: 涓婁笅鏂囦欢淇℃伅
        @type context: ServantProxy.mapcls_context
        @param status: 鐘舵€佷俊鎭?
        @type status:
        @return: 鍝嶅簲鎶ユ枃
        @rtype: ResponsePacket
        '''
        tarsLogger.debug('ServantProxy:tars_invoke, func: %s', sFuncName)
        req = RequestPacket()
        req.iVersion = ServantProxy.TARSVERSION
        req.cPacketType = cPacketType
        req.iMessageType = ServantProxy.TARSMESSAGETYPENULL
        req.iRequestId = 0
        req.sServantName = self.tars_name()
        req.sFuncName = sFuncName
        req.sBuffer = sBuffer
        req.iTimeout = self.tars_timeout()

        reqmsg = ReqMessage()
        reqmsg.type = ReqMessage.SYNC_CALL
        reqmsg.servant = self
        reqmsg.lock = threading.Condition()
        reqmsg.request = req
        reqmsg.begtime = time.time()
        # # test
        reqmsg.isHash = True
        reqmsg.isConHash = True
        reqmsg.hashCode = 123456

        rsp = None
        try:
            rsp = self.__invoke(reqmsg)
        except exception.TarsSyncCallTimeoutException:
            if reqmsg.adapter:
                reqmsg.adapter.finishInvoke(True)
            raise
        except TarsException:
            raise
        except:
            raise TarsException('ServantProxy::tars_invoke excpetion')

        if reqmsg.adapter:
            reqmsg.adapter.finishInvoke(False)

        return rsp

    def tars_invoke_async(self, cPacketType, sFuncName, sBuffer,
                          context, status, callback):
        '''
        @brief: TARS鍗忚鍚屾鏂规硶璋冪敤
        @param cPacketType: 璇锋眰鍖呯被鍨?
        @type cPacketType: int
        @param sFuncName: 璋冪敤鍑芥暟鍚?
        @type sFuncName: str
        @param sBuffer: 搴忓垪鍖栧悗鐨勫彂閫佸弬鏁?
        @type sBuffer: str
        @param context: 涓婁笅鏂囦欢淇℃伅
        @type context: ServantProxy.mapcls_context
        @param status: 鐘舵€佷俊鎭?
        @type status:
        @param callback: 寮傛璋冪敤鍥炶皟瀵硅薄
        @type callback: ServantProxyCallback鐨勫瓙绫?
        @return: 鍝嶅簲鎶ユ枃
        @rtype: ResponsePacket
        '''
        tarsLogger.debug('ServantProxy:tars_invoke')
        req = RequestPacket()
        req.iVersion = ServantProxy.TARSVERSION
        req.cPacketType = cPacketType if callback else ServantProxy.TARSONEWAY
        req.iMessageType = ServantProxy.TARSMESSAGETYPENULL
        req.iRequestId = 0
        req.sServantName = self.tars_name()
        req.sFuncName = sFuncName
        req.sBuffer = sBuffer
        req.iTimeout = self.tars_timeout()

        reqmsg = ReqMessage()
        reqmsg.type = ReqMessage.ASYNC_CALL if callback else ReqMessage.ONE_WAY
        reqmsg.callback = callback
        reqmsg.servant = self
        reqmsg.request = req
        reqmsg.begtime = time.time()

        rsp = None
        try:
            rsp = self.__invoke(reqmsg)
        except TarsException:
            raise
        except Exception:
            raise TarsException('ServantProxy::tars_invoke excpetion')

        if reqmsg.adapter:
            reqmsg.adapter.finishInvoke(False)

        return rsp

    def __timeout(self):
        '''
        @brief: 鑾峰彇瓒呮椂鏃堕棿锛屽崟浣嶆槸s
        @return: 瓒呮椂鏃堕棿
        @rtype: float
        '''
        return self.__object.timeout()

    def __invoke(self, reqmsg):
        '''
        @brief: 杩滅▼杩囩▼璋冪敤
        @param reqmsg: 璇锋眰鏁版嵁
        @type reqmsg: ReqMessage
        @return: 璋冪敤鎴愬姛鎴栧け璐?
        @rtype: bool
        '''
        tarsLogger.debug('ServantProxy:invoke, func: %s',
                         reqmsg.request.sFuncName)
        ret = self.__object.invoke(reqmsg)
        if ret == -2:
            errmsg = ('ServantProxy::invoke fail, no valid servant,' +
                      ' servant name : %s, function name : %s' %
                      (reqmsg.request.sServantName,
                       reqmsg.request.sFuncName))
            raise TarsException(errmsg)
        if ret == -1:
            errmsg = ('ServantProxy::invoke connect fail,' +
                      ' servant name : %s, function name : %s, adapter : %s' %
                      (reqmsg.request.sServantName,
                       reqmsg.request.sFuncName,
                       reqmsg.adapter.getEndPointInfo()))
            raise TarsException(errmsg)
        elif ret != 0:
            errmsg = ('ServantProxy::invoke unknown fail, ' +
                      'Servant name : %s, function name : %s' %
                      (reqmsg.request.sServantName,
                       reqmsg.request.sFuncName))
            raise TarsException(errmsg)

        if reqmsg.type == ReqMessage.SYNC_CALL:
            reqmsg.lock.acquire()
            reqmsg.lock.wait(self.__timeout())
            reqmsg.lock.release()

            if not reqmsg.response:
                errmsg = ('ServantProxy::invoke timeout: %d, servant name'
                          ': %s, adapter: %s, request id: %d' % (
                              self.tars_timeout(),
                              self.tars_name(),
                              reqmsg.adapter.trans().getEndPointInfo(),
                              reqmsg.request.iRequestId))
                raise exception.TarsSyncCallTimeoutException(errmsg)
            elif reqmsg.response.iRet == ServantProxy.TARSSERVERSUCCESS:
                return reqmsg.response
            else:
                errmsg = 'servant name: %s, function name: %s' % (
                         self.tars_name(), reqmsg.request.sFuncName)
                self.tarsRaiseException(reqmsg.response.iRet, errmsg)

    def _finished(self, reqmsg):
        '''
        @brief: 閫氱煡杩滅▼杩囩▼璋冪敤绾跨▼鍝嶅簲鎶ユ枃鍒颁簡
        @param reqmsg: 璇锋眰鍝嶅簲鎶ユ枃
        @type reqmsg: ReqMessage
        @return: 鍑芥暟鎵ц鎴愬姛鎴栧け璐?
        @rtype: bool
        '''
        tarsLogger.debug('ServantProxy:finished')
        if not reqmsg.lock:
            return False
        reqmsg.lock.acquire()
        reqmsg.lock.notifyAll()
        reqmsg.lock.release()
        return True

    def tarsRaiseException(self, errno, desc):
        '''
        @brief: 鏈嶅姟鍣ㄨ皟鐢ㄥけ璐ワ紝鏍规嵁鏈嶅姟绔粰鐨勯敊璇爜鎶涘嚭寮傚父
        @param errno: 閿欒鐮?
        @type errno: int
        @param desc: 閿欒鎻忚堪
        @type desc: str
        @return: 娌℃湁杩斿洖鍊硷紝鍑芥暟浼氭姏鍑哄紓甯?
        @rtype:
        '''
        if errno == ServantProxy.TARSSERVERSUCCESS:
            return

        elif errno == ServantProxy.TARSSERVERDECODEERR:
            raise exception.TarsServerDecodeException(
                "server decode exception: errno: %d, msg: %s" % (errno, desc))

        elif errno == ServantProxy.TARSSERVERENCODEERR:
            raise exception.TarsServerEncodeException(
                "server encode exception: errno: %d, msg: %s" % (errno, desc))

        elif errno == ServantProxy.TARSSERVERNOFUNCERR:
            raise exception.TarsServerNoFuncException(
                "server function mismatch exception: errno: %d, msg: %s" % (errno, desc))

        elif errno == ServantProxy.TARSSERVERNOSERVANTERR:
            raise exception.TarsServerNoServantException(
                "server servant mismatch exception: errno: %d, msg: %s" % (errno, desc))

        elif errno == ServantProxy.TARSSERVERRESETGRID:
            raise exception.TarsServerResetGridException(
                "server reset grid exception: errno: %d, msg: %s" % (errno, desc))

        elif errno == ServantProxy.TARSSERVERQUEUETIMEOUT:
            raise exception.TarsServerQueueTimeoutException(
                "server queue timeout exception: errno: %d, msg: %s" % (errno, desc))

        elif errno == ServantProxy.TARSPROXYCONNECTERR:
            raise exception.TarsServerQueueTimeoutException(
                "server connection lost: errno: %d, msg: %s" % (errno, desc))

        else:
            raise exception.TarsServerUnknownException(
                "server unknown exception: errno: %d, msg: %s" % (errno, desc))
