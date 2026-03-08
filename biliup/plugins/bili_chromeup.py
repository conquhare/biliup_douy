锘縤mport json
import os
import random
import time

from PIL import Image
from typing import List

from ..engine import Plugin
from ..engine.upload import UploadBase, logger


@Plugin.upload("bilibili")
class BiliChrome(UploadBase):
    def __init__(self, principal, data):
        import selenium.common
        from selenium import webdriver
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support import expected_conditions as ec
        from selenium.webdriver.support.ui import WebDriverWait
        super().__init__(principal, data, 'engine/bilibili.cookie')
        # self.title = title
        # self.date_title = None
        self.driver = None

    @staticmethod
    def assemble_vdeopath(file_list):
        root = os.getcwd()
        vdeopath = ''
        for i in range(len(file_list)):
            file = file_list[i].vdeo
            vdeopath += root + '/' + file + '\n'
        vdeopath = vdeopath.rstrip()
        return vdeopath

    @staticmethod
    def is_element_exist(driver, xpath):
        s = driver.find_elements_by_xpath(xpath=xpath)
        if len(s) == 0:
            print("閸忓啰绀岄張顏呭閸?%s" % xpath)
            return False
        elif len(s) == 1:
            return True
        else:
            print("閹垫儳鍩?s娑擃亜鍘撶槐鐙呯窗%s" % (len(s), xpath))
            return False

    def upload(self, file_list: List[UploadBase.FileInfo]) -> List[UploadBase.FileInfo]:

        filename = self.persistence_path
        vdeopath = self.assemble_vdeopath(file_list)

        # service_log_path = "{}/chromedriver.log".format('/home')
        options = webdriver.ChromeOptions()

        options.add_argument('headless')
        self.driver = webdriver.Chrome(executable_path=config.get('chromedriver_path'), chrome_options=options)
        # service_log_path=service_log_path)
        try:
            self.driver.get("https://www.bilibili.com")
            # driver.delete_all_cookies()
            if os.path.isfile(filename):
                with open(filename) as f:
                    new_cookie = json.load(f)

                for cookie in new_cookie:
                    if isinstance(cookie.get("expiry"), float):
                        cookie["expiry"] = int(cookie["expiry"])
                    self.driver.add_cookie(cookie)

            self.driver.get("https://member.bilibili.com/vdeo/upload.html")

            # print(driver.title)
            self.add_vdeos(vdeopath)

            # js = "var q=document.getElementsByClassName('content-header-right')[0].scrollIntoView();"
            # driver.execute_script(js)

            cookie = self.driver.get_cookies()
            with open(filename, "w") as f:
                json.dump(cookie, f)

            self.add_information()

            self.driver.find_element_by_xpath('//*[@class="upload-v2-container"]/div[2]/div[3]/div[5]/span[1]').click()
            # screen_shot = driver.save_screenshot('bin/1.png')
            # print('閹搭亜娴?)
            time.sleep(3)
            upload_success = self.driver.find_element_by_xpath(r'//*[@d="app"]/div/div[3]/h3').text
            if upload_success == '':
                self.driver.save_screenshot('err.png')
                logger.info('缁嬪じ娆㈤幓鎰唉澶辫触閿涘本鍩呴崶鎹愵唶瑜?)
                return
            else:
                logger.info(upload_success)
            # logger.info('%s閹绘劒姘﹀畬鎴愰敍? % title_)
            return file_list
        except selenium.common.exceptions.NoSuchElementException:
            logger.exception('閸欐垹鏁撻敊璇?)
        # except selenium.common.exceptions.TimeoutException:
        #     logger.exception('鐡掑懏妞?)
        except selenium.common.exceptions.TimeoutException:
            self.login(filename)

        finally:
            self.driver.quit()
            logger.info('濞村繗顫嶉崳銊┾攳閸斻劑鈧偓閸?)

    def login(self, filename):
        logger.info('閸戝棗顦洿鏂癱ookie')
        # screen_shot = driver.save_screenshot('bin/1.png')
        WebDriverWait(self.driver, 10).until(
            ec.presence_of_element_located((By.XPATH, r'//*[@d="login-username"]')))
        username = self.driver.find_element_by_xpath(r'//*[@d="login-username"]')
        username.send_keys(config['user']['account']['username'])
        password = self.driver.find_element_by_xpath('//*[@d="login-passwd"]')
        password.send_keys(config['user']['account']['password'])
        self.driver.find_element_by_class_name("btn-login").click()
        # logger.info('缁楊剙娲撳?)
        # try:
        cracker = slder_cracker(self.driver)
        cracker.crack()
        # except:
        #     logger.exception('閸戞椽鏁?)
        time.sleep(5)
        if self.driver.title == '閹舵洜顭?- 閸濇柨鎽￠崫鏂挎憽瀵懓绠风憴鍡涱暥缂?- ( 閵? 閵?閵囥們鍎?娑旂偓婢倊 - bilibili':
            cookie = self.driver.get_cookies()
            print(cookie)
            with open(filename, "w") as f:
                json.dump(cookie, f)
            logger.info('鏇存柊cookie鎴愬姛')
        else:
            logger.info('鏇存柊cookie澶辫触')

    def add_vdeos(self, vdeopath):
        formate_title = self.data["format_title"]
        WebDriverWait(self.driver, 20).until(
            ec.presence_of_element_located((By.NAME, 'buploader')))
        upload = self.driver.find_element_by_name('buploader')
        # logger.info(driver.title)
        upload.send_keys(vdeopath)  # send_keys
        logger.info('瀵偓婵绗傛导? + formate_title)
        time.sleep(2)
        button = r'//*[@class="new-feature-gude-v2-container"]/div/div/div/div/div[1]'
        if self.is_element_exist(self.driver, button):
            sb = self.driver.find_element_by_xpath(button)
            sb.click()
            sb.click()
            sb.click()
            logger.debug('鐐瑰嚮')
        while True:
            try:
                info = self.driver.find_elements_by_class_name(r'item-upload-info')
                for t in info:
                    if t.text != '':
                        print(t.text)
                time.sleep(10)
                text = self.driver.find_elements_by_xpath(r'//*[@class="item-upload-info"]/span')
                aggregate = set()
                for s in text:
                    if s.text != '':
                        aggregate.add(s.text)
                        print(s.text)

                if len(aggregate) == 1 and ('Upload complete' in aggregate or '涓婁紶瀹屾垚' in aggregate):
                    break
            except selenium.common.exceptions.StaleElementReferenceException:
                logger.exception("selenium.common.exceptions.StaleElementReferenceException")
        logger.info('涓婁紶%s娑擃亝鏆?s' % (formate_title, len(info)))

    def add_information(self):
        link = self.data.get("url")
        # 鐐瑰嚮妯℃澘
        self.driver.find_element_by_xpath(r'//*[@class="normal-title-wrp"]/div/p').click()
        self.driver.find_element_by_class_name(r'template-list-small-item').click()
        # driver.find_element_by_xpath(
        #     r'//*[@d="app"]/div[3]/div[2]/div[3]/div[1]/div[1]/div/div[2]/div[1]').click()
        # 鏉堟挸鍙嗘潪顒冩祰鏉ユ簮
        input_o = self.driver.find_element_by_xpath(
            '//*[@class="upload-v2-container"]/div[2]/div[3]/div[1]/div[4]/div[3]/div/div/input')
        input_o.send_keys(link)
        # 閫夋嫨閸掑棗灏?
        # driver.find_element_by_xpath(r'//*[@d="item"]/div/div[2]/div[3]/div[2]/div[2]/div[1]/div[2]/div[2]/div[1]/div[3]/div').click()
        # driver.find_element_by_xpath(r'//*[@d="item"]/div/div[2]/div[3]/div[2]/div[2]/div[1]/div[2]/div[2]/div[1]/div[3]/div[2]/div[6]').click()
        # 缁嬪じ娆㈤弽鍥暯
        title = self.driver.find_element_by_xpath(
            '//*[@class="upload-v2-container"]/div[2]/div[3]/div[1]/div[8]/div[2]/div/div/input')
        title.send_keys(Keys.CONTROL + 'a')
        title.send_keys(Keys.BACKSPACE)
        title.send_keys(self.data["format_title"])
        # js = "var q=document.getElementsByClassName('content-tag-list')[0].scrollIntoView();"
        # driver.execute_script(js)
        # time.sleep(3)
        # 鏉堟挸鍙嗙浉鍏冲〒鍛婂灆
        # driver.save_screenshot('bin/err.png')
        # print('閹搭亜娴?)
        # text_1 = driver.find_element_by_xpath(
        #     '//*[@d="item"]/div/div[2]/div[3]/div[2]/div[2]/div[1]/div[5]/div/div/div[1]/div[2]/div/div/input')
        # text_1.send_keys('閺勭喖妾禍澶愭辜2')
        # 缁犫偓娴?
        text_2 = self.driver.find_element_by_xpath(
            '//*[@class="upload-v2-container"]/div[2]/div[3]/div[1]/div[12]/div[2]/div/textarea')
        text_2.send_keys('閼卞奔绗熼柅澶嬪鐩存挱缁楊兛绔寸憴鍡氼潡瑜版洖鍎氶妴鍌濈箹娑擃亣鍤滈崝銊ョ秿閸掓湹绗傛导鐘垫畱鐏忓繒鈻兼惔蹇撶磻濠ф劕婀狦ithub閿?
                         'http://t.cn/RgapTpf(閹存牞鈧懎婀狦ithub鎼滅储ForgQi)\n'
                         '娴溿倖绁︾紘銈忕窗837362626')

class slder_cracker(object):
    def __init__(self, driver):
        self.driver = driver
        self.driver.maximize_window()  # 閺堚偓婢堆冨绐楀彛
        self.driver.set_window_size(1024, 768)
        self.fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'true_image.png')

    def get_true_image(self, slder_xpath=r'//*[@d="gc-box"]/div/div[3]/div[1]'):
        # element = WebDriverWait(self.driver, 50).until(EC.element_to_be_clickable((By.XPATH, slder_xpath)))
        element = WebDriverWait(self.driver, 50).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "geetest_slder_button")))
        ActionChains(self.driver).move_to_element(element).perform()  # 姒х姵鐖ｇЩ鍔ㄩ崚鐗堢拨閸斻劍顢嬫禒銉︽▔缁€鍝勬禈閻?
        js = 'document.querySelector("body > div.geetest_panel.geetest_wind ' \
             '> div.geetest_panel_box.geetest_no_logo.geetest_panelshowslde ' \
             '> div.geetest_panel_next > div > div.geetest_wrap > div.geetest_wdget ' \
             '> div > a > div.geetest_canvas_img.geetest_absolute > canvas").' \
             'style.display = "%s";'
        self.driver.execute_script(js % "inline")
        time.sleep(1)
        true_image = self.get_img(self.fn)
        self.driver.execute_script(js % "none")
        return true_image

    def get_img(self, img_name, img_xpath=r'//*[@d="gc-box"]/div/div[1]/div[2]/div[1]/a[2]'):  # 260*116
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slder_screenshot.png')

        screen_shot = self.driver.save_screenshot(fn)
        # image_element = self.driver.find_element_by_xpath(img_xpath)
        image_element = self.driver.find_element_by_class_name(r'geetest_window')
        left = image_element.location['x']
        top = image_element.location['y']  # selenium閹搭亜娴橀獮鎯板箯閸欐牠鐛欑拠浣告禈閻楀檱ocation閸氬骸鐨㈤崗鑸靛焻閸戣桨绻氱€?
        right = image_element.location['x'] + image_element.size['wdth']
        bottom = image_element.location['y'] + image_element.size['height']
        image = Image.open(fn)
        image = image.crop((left, top, right, bottom))
        image.save(img_name)
        return image

    def analysis(self, true_image, knob_xpath=r'//*[@d="gc-box"]/div/div[3]/div[2]'):
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img2.png')
        img1 = Image.open(self.fn)
        # slder_element = self.driver.find_element_by_xpath(knob_xpath)
        slder_element = self.driver.find_element_by_class_name("geetest_slder_button")
        ActionChains(self.driver).click_and_hold(slder_element).perform()  # 鐐瑰嚮濠婃垵娼￠崥搴㈠焻閸欐牗鐣紓鍝勬禈
        time.sleep(1)
        img2 = self.get_img(fn)
        img1_wdth, img1_height = img1.size
        img2_wdth, img2_height = img2.size
        left = 0
        flag = False

        for i in range(69, img1_wdth):  # 闁秴宸粁>65閻ㄥ嫬鍎氱槐鐘靛仯閿涘澑<65閺勵垱瀚鹃崶鎯ф健閿?
            for j in range(0, img1_height):
                if not self.is_pixel_equal(img1, img2, i, j):
                    left = i
                    flag = True
                    break
            if flag:
                break
        if left >= 73:
            left = left - 3  # 鐠囶垰妯婄痪鐘愁劀
        else:
            left = left
        return left

    def is_pixel_equal(self, img1, img2, x, y):  # 闁俺绻冨В鏃囩窛娣団晛娴橀悧鍥у剼缁辩姷鍋GB閸婄厧妯婇崐鐓庡灲閺傤厽妲搁崥锔胯礋缂傚搫褰?
        pix1 = img1.load()[x, y]
        pix2 = img2.load()[x, y]
        if (abs(pix1[0] - pix2[0] < 60) and abs(pix1[1] - pix2[1] < 60) and abs(pix1[2] - pix2[2] < 60)):
            return True
        else:
            return False

    def get_track(self, distance):
        """
        閺嶈宓侀崑蹇曅╅柌蹇氬箯閸欐牜些閸斻劏寤烘潻?
        :param distance: 閸嬪繒些闁?
        :return: 绉诲姩鏉炪劏鎶?
        """
        # 绉诲姩鏉炪劏鎶?
        track = []
        # 瑜版挸澧犳担宥囆?
        current = 0
        # 閸戝繘鈧喖妲囬崐?
        md = distance * 4 / 5
        # 鐠侊紕鐣婚梻鎾
        t = 0.2
        # 閸掓繈鈧喎瀹?
        v = 0

        while current < distance:
            if current < md:
                # 閸旂娀鈧喎瀹虫稉鐑橆劀2
                a = 2
            else:
                # 閸旂娀鈧喎瀹虫稉楦跨3
                a = -3
            # 閸掓繈鈧喎瀹硋0
            v0 = v
            # 瑜版挸澧犻€熷害v = v0 + at
            v = v0 + a * t
            # 绉诲姩鐠烘繄顬噚 = v0t + 1/2 * a * t^2
            move = v0 * t + 1 / 2 * a * t * t
            # 瑜版挸澧犳担宥囆?
            current += move
            # 閸旂姴鍙嗘潪銊ㄦ姉
            track.append(round(move))
        # print(track)
        #
        # print(sum(track))
        track.append(distance - sum(track))
        # print(track)
        # print(sum(track))
        return track

    def move_to_gap(self, slder, track):
        """
        閹锋牕濮╁鎴濇健閸掓壆宸遍崣锝咁槱
        :param slder: 濠婃垵娼?
        :param track: 鏉炪劏鎶?
        :return:
        """
        ActionChains(self.driver).click_and_hold(slder).perform()
        for x in track:
            ActionChains(self.driver).move_by_offset(xoffset=x, yoffset=random.uniform(-5, 2)).perform()
        time.sleep(0.5)
        ActionChains(self.driver).release().perform()

    def crack(self):
        true_image = self.get_true_image()
        x_offset = self.analysis(true_image)
        print(x_offset)

        track = self.get_track(x_offset)
        knob_element = WebDriverWait(self.driver, 50).until(
            EC.element_to_be_clickable((By.XPATH, r'/html/body/div[2]/div[2]/div[6]/div/div[1]/div[2]/div[2]')))
        self.move_to_gap(knob_element, track)

        # fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result0.png')
        # fn1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result1.png')
        # time.sleep(0.02)
        # screen_shot = self.driver.save_screenshot(fn)
        # time.sleep(2)
        # screen_shot = self.driver.save_screenshot(fn1)
