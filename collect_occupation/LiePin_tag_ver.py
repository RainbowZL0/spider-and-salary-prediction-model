import os.path
import random
import re
import time

import joblib
import pandas as pd
from colorama import Fore, init
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

PAGES = 10
BREAK = '$'
OUTPUT_FOLDER = "./OUTPUT_FOLDER"
init(autoreset=True)


class CollectData:
    def __init__(self):
        options = Options()
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-popup-blocking")
        # 创建浏览器实例并设置选项
        self.driver = webdriver.Chrome(options=options)

        self.action = ActionChains(self.driver)

        self.occupation_links_list = list()
        self.job_cards_list_for_one_page = list()

        self.now_displayed_link = None

        self.df = create_new_dataframe()

    def get_occupation_link_list(self):
        """
        获得各个行业的link list
        """
        self.driver.get("https://www.liepin.com/")

        # 鼠标移动到菜单上悬停
        WebDriverWait(self.driver, 10).until(
            ec.element_to_be_clickable((By.CLASS_NAME, 'hot-jobs-first-item')))

        menu = self.driver.find_element(By.CLASS_NAME, 'hot-jobs-first-item')
        self.action.move_to_element(menu).perform()

        menu_name = menu.find_element(By.CLASS_NAME,
                                      'hot-jobs-first-title.hot-jobs-first-title-active').text
        assert menu_name == "IT/互联网"

        # IT/互联网内，多个子菜单area
        sub_menus = menu.find_elements(By.CLASS_NAME, 'hot-jobs-second-item')
        occupation_link_list = list()
        for sub_menu in sub_menus:
            sub_menu_dict = get_link_from_one_sub_menu(sub_menu)
            occupation_link_list.append(sub_menu_dict)
            # break  # 第一个子菜单是后端开发。

        self.occupation_links_list = occupation_link_list

    def collect_data_from_sub_menu_area(self, sub_menu_dict: dict):
        """
        获取一个area内所有occupation的data.
        :param sub_menu_dict: 形如{'area': ..., 'occupation_list': [{},{}]}
        :type sub_menu_dict: dict
        :return:
        :rtype:
        """
        area_name = sub_menu_dict['area']
        occupation_link_list = sub_menu_dict['occupation_list']

        random.shuffle(occupation_link_list)

        for occupation_and_link_dict in occupation_link_list:
            self.collect_data_from_one_occupation(area_name, occupation_and_link_dict)

    def collect_data_from_one_occupation(self, area_name, occupation_dict: dict):
        """

        :param area_name:
        :type area_name:
        :param occupation_dict:
        :type occupation_dict:
        :return:
        :rtype:
        """
        # 创建输出文件所在的文件夹
        area_name = clean_path_sign_in_file_name(area_name)  # 清理area中的路径符号
        output_folder = os.path.join(OUTPUT_FOLDER, area_name)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        # 指定输出文件的目录
        occupation_name = occupation_dict['occupation']
        output_file_name = occupation_name + ".xlsx"
        output_file_name = clean_path_sign_in_file_name(output_file_name)  # 清理output_file_name中的路径符号
        output_file_path = os.path.join(output_folder, output_file_name)

        print(f"{Fore.GREEN}Now collecting data of {output_file_path}")  # 正在处理...

        # 跳转页面
        link = occupation_dict['link']
        self.driver.get(link)

        # 开始收集数据
        one_occupation_list = list()
        # 第1页的收集
        self.close_login()

        has_content, one_page_list = self.collect_info_from_one_page()
        if not has_content:
            pass  # 若第一页就没有数据，就什么都不做。
        else:
            one_occupation_list += one_page_list  # 若第一页有数据，则加入第一页的。然后处理后续的页
            # 后续页的收集。总共PAGES页
            for i in range(1, PAGES):
                self.close_login()  # 判断是否出现了登录框，若出现则关闭

                has_next_page = self.click_next_page()  # 下一页
                if not has_next_page:
                    break

                has_content, one_page_list = self.collect_info_from_one_page()  # 若该页没有card，则会返回False。否则返回list
                if not has_next_page:
                    break  # 若本页没有card，则退出循环，不再进入下一页。
                else:
                    one_occupation_list += one_page_list

            # 转为dataframe
            df = pd.DataFrame(one_occupation_list)
            # 添加行业列，例如取值为Java
            new_column = pd.Series([occupation_name] * len(df))
            df["行业"] = new_column
            # 输出
            df.to_excel(output_file_path, index=False)

    def collect_info_from_one_page(self):
        """
        获取一页的list(dict())，每个dict都是一个card的信息
        :return: has_content, one_page_list
        :rtype: bool, list
        """
        self.get_job_cards_from_one_page()  # 把这一个page的card都准备好
        # 初始化返回值
        one_page_list = list()

        if len(self.job_cards_list_for_one_page) == 0:  # 若没有card，返回False
            has_content = False
            return has_content, one_page_list
        else:
            has_content = True
            for card in self.job_cards_list_for_one_page:
                one_card_dict = self.get_info_from_one_card(card)  # 一个card信息的dict
                one_page_list.append(one_card_dict)  # 本页信息的list中加入card的dict
            return has_content, one_page_list

    def get_job_cards_from_one_page(self):
        """
        Note that a page should be opened before calling this method.
        :return: job cards for one page
        :rtype: WebElement
        """
        self.close_login()
        # Wait until the web page is well loaded.
        # WebDriverWait(self.driver, 10).until(ec.element_to_be_clickable((By.CLASS_NAME, "job-detail-box")))
        # Collect the job-detail-box
        job_detail_boxes_list = self.driver.find_elements(By.CLASS_NAME, 'job-detail-box')
        self.job_cards_list_for_one_page = job_detail_boxes_list

    def close_login_v2(self):
        login_frame_list = self.driver.find_elements(By.CLASS_NAME, 'ant-modal-confirm-body')
        if len(login_frame_list) != 0:  # 若list不为空，则说明弹出了登录框
            login_frame = self.driver.find_element(By.CLASS_NAME, 'ant-modal-confirm-body')
            close_button = login_frame.find_elements(By.TAG_NAME, 'div')[-1]
            close_button.click()

    def close_login(self):
        pass

    def click_next_page(self):
        """
        点击下一页
        """
        # self.driver.delete_all_cookies()
        self.close_login()
        # 下一页按钮，是底部几个页码的按钮中的最后一个。
        button_exist_list = self.driver.find_elements(By.CLASS_NAME, 'ant-pagination')
        if len(button_exist_list) != 0:
            WebDriverWait(self.driver, 10).until(ec.element_to_be_clickable((By.CLASS_NAME, 'ant-pagination')))
            next_page_button = self.driver.find_element(By.CLASS_NAME, 'ant-pagination'). \
                find_elements(By.TAG_NAME, 'a')[-1]
            next_page_button.click()
            return True
        else:
            return False

    def get_info_from_one_card(self, job_detail_box: WebElement):
        """
        返回这一条招聘信息对应的dict
        :param job_detail_box: 一条招聘信息的card
        :type job_detail_box: WebElement
        :return: 一个dict
        :rtype: dict
        """
        self.close_login()

        job_detail_header_box = job_detail_box.find_element(By.CLASS_NAME, 'job-detail-header-box')
        job_labels_box = job_detail_box.find_element(By.CLASS_NAME, 'job-labels-box')
        job_company_info_box = job_detail_box.find_element(By.CLASS_NAME, 'job-company-info-box')

        # 包括：职位，工作地点
        job_title_box = job_detail_header_box.find_element(By.CLASS_NAME, 'job-title-box')
        # 包括：薪水
        job_salary = job_detail_header_box.find_element(By.CLASS_NAME, 'job-salary')

        data_job_name = job_title_box.find_element(By.CLASS_NAME, 'ellipsis-1').text

        job_dq_box_exist_list = job_title_box.find_elements(By.CLASS_NAME, 'job-dq-box')
        if len(job_dq_box_exist_list) != 0:
            data_job_place = job_title_box.find_element(By.CLASS_NAME, 'job-dq-box'). \
                find_element(By.CLASS_NAME, 'ellipsis-1').text
        else:
            data_job_place = ""

        data_salary = job_salary.text

        # 包括：工作经验，学历
        data_work_exp, data_education, data_job_tags = prepare_job_tags(job_labels_box)
        # 包括：公司，公司标签
        data_company_name, data_company_tags = prepare_company_tags(job_company_info_box)

        one_card_dict = {
            '职位': data_job_name,
            '公司': data_company_name,
            '薪水': data_salary,
            '学历要求': data_education,
            '工作经验': data_work_exp,
            '工作地点': data_job_place,
            '标签': data_job_tags,
            '公司标签': data_company_tags
        }

        return one_card_dict

    def login_in(self):
        # banner = self.driver.find_element(
        #     By.CLASS_NAME,
        #     'home-banner-login-box.common-page-container'
        # )
        # banner_compo = banner.find_elements(
        #     By.TAG_NAME,
        #     'div'
        # )
        # switch_to_login_with_password = None
        # for elem in banner_compo:
        #     if elem.text == "密码登录":
        #         switch_to_login_with_password = elem
        #         break

        start_login = self.driver.find_element(
            By.CLASS_NAME,
            'header-menu-item.header-quick-menu-not-login-item'
        )
        self.action.move_to_element(start_login)
        self.action.click().perform()

        account_frame = self.driver.find_element(
            By.CLASS_NAME,
            'ant-form-item-control-input'
        )
        password_frame = self.driver.find_element(
            By.CLASS_NAME,
            'ant-input.ant-input-lg'
        )
        login_button = self.driver.find_element(
            By.CLASS_NAME,
            'ant-btn.ant-btn-primary.ant-btn-round.ant-btn-lg.login-submit-btn'
        )

        account_frame.send_keys('13701216049')
        password_frame.send_keys('Make@1036')
        login_button.click()

    def get_cookies(self):
        self.driver.get("https://www.liepin.com/")

        time.sleep(1)

        self.driver.get("https://www.liepin.com/career/java/")
        cookies = self.driver.get_cookies()

        joblib.dump(cookies, 'cookies.pkl')

    def load_cookies(self):
        self.driver.get("https://www.liepin.com/career/java/")

        self.driver.delete_all_cookies()

        cookies = joblib.load('cookies.pkl')
        for cookie in cookies:
            self.driver.add_cookie(cookie)

        self.driver.refresh()


def clean_path_sign_in_file_name(string: str):
    chars_to_remove = '\\/'
    pattern = f'[{re.escape(chars_to_remove)}]'
    return re.sub(pattern=pattern,
                  repl="-",
                  string=string)


def get_link_from_one_sub_menu(sub_menu: WebElement):
    """
    返回值形如：
    {
        '后端开发': [{'Java': 'https://..'}, {}, {} ...]
    }
    :param sub_menu: 一个子领域的card。例如后端开发
    :type sub_menu: WebElement
    :return: link list from one sub menu
    :rtype: list
    """
    title = sub_menu.find_element(By.CLASS_NAME, 'hot-jobs-second-title').text

    link_dict_list = list()
    content_list = sub_menu.find_element(By.CLASS_NAME, 'hot-jobs-second-content'). \
        find_elements(By.CLASS_NAME, 'hot-jobs-three-title')
    for content in content_list:
        # 分别获得行业名和link
        occupation = content.text
        link = content.get_attribute('href')
        # 将二者存入一个dict
        dictionary = {
            'occupation': occupation,
            'link': link
        }
        link_dict_list.append(dictionary)

    sub_menu_dict = {
        'area': title,
        'occupation_list': link_dict_list
    }

    return sub_menu_dict


def prepare_job_tags(elem: WebElement):
    """
    处理job tags。提取出前两条：工作经验，学历。其余的join成一个长字符串。用全局变量BREAK连接。
    :param elem: job tags所属的WebElement
    :type elem: WebElement
    :return: 工作经验，学历，其他tag组成的字符串
    :rtype: str
    """
    tags = elem.find_elements(By.CLASS_NAME, 'labels-tag')

    # 单独取出前两条，分别是工作经验和学历
    work_exp = tags[0].text
    education = tags[1].text
    tags = tags[2:]  # remove the first and the second

    # 处理其余的标签，join成一个长字符串，用$连接
    if len(tags) == 0:
        other_tags_str = ""
    else:
        tags_str_list = convert_to_str_list(tags)
        other_tags_str = BREAK.join(tags_str_list)

    return work_exp, education, other_tags_str


def prepare_company_tags(elem: WebElement):
    company_name = elem.find_element(By.CLASS_NAME, 'company-name.ellipsis-1').text

    tags_list = elem.find_elements(By.CLASS_NAME, 'company-tags-box.ellipsis-1')
    if len(tags_list) != 0:
        tags = tags_list[0].find_elements(By.TAG_NAME, 'span')
        tags_str_list = convert_to_str_list(tags)
        tags_str = BREAK.join(tags_str_list)
    else:
        tags_str = ""
    return company_name, tags_str


def convert_to_str_list(web_element: list):
    """
    修改list的每个元素类型为str
    :param web_element: 原list
    :type web_element: list
    :return: 修改后的list
    :rtype: list
    """
    for index, element in enumerate(web_element):
        element_str = element.text
        web_element[index] = element_str
    return web_element


def create_new_dataframe():
    """
    创建一个新的dataframe。因为复用次数太多，只写一遍，以后调用这个函数即可。
    :return: 空dataframe
    :rtype: pd.DataFrame
    """
    return pd.DataFrame(columns=["职位", "公司", "薪水", "学历要求", "工作经验", "工作地点", "标签", "公司标签"])


def start():
    collect_data = CollectData()

    collect_data.get_occupation_link_list()
    collect_data.load_cookies()

    for sub_menu_dict in collect_data.occupation_links_list:
        collect_data.collect_data_from_sub_menu_area(sub_menu_dict=sub_menu_dict)

    collect_data.driver.close()


if __name__ == '__main__':
    start()
