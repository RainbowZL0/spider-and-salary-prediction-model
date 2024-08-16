import time

import joblib
import pandas as pd
import selenium
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class CollectData:
    def __init__(self):
        options = Options()
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-popup-blocking")

        # 创建浏览器实例并设置选项
        self.driver = webdriver.Chrome(options=options)

        self.action = ActionChains(self.driver)

        self.now_link: str = ""
        self.occupation_links_list = list()
        self.job_cards_list_for_one_page = list()

    def get_occupation_link_list(self):
        """
        获得各个行业的link list
        """
        self.driver.get("https://www.zhipin.com/?city=100010000&ka=city-sites-100010000")

        # 鼠标移动到菜单上悬停
        menu = self.driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div/div[1]/dl[1]/dd')
        self.action.move_to_element(menu).perform()
        time.sleep(1)

        # class_name为text对应的是“后端开发”领域
        text = self.driver.find_element(By.CLASS_NAME, 'text')
        buttons = text.find_elements(By.TAG_NAME, 'a')
        for button in buttons:
            link = button.get_attribute('href')
            self.occupation_links_list.append(link)

    def collect_info_from_one_page(self):
        pass

    def get_job_cards_from_one_page(self):
        """
        Note that a page should be opened before calling this method.
        :return: job cards for one page
        :rtype: WebElement
        """
        job_list_box = self.driver.find_element(By.CLASS_NAME, 'job-list-box')
        self.job_cards_list_for_one_page = job_list_box.find_elements(By.CLASS_NAME, 'job-card-wrapper')


def get_info_from_one_card(card: WebElement):
    job_card_body = card.find_element(By.CLASS_NAME, 'job-card-body.clearfix')
    get_info_from_card_body(job_card_body)

    job_card_footer = card.find_element(By.CLASS_NAME, 'job-card-footer.clearfix')


def get_info_from_card_body(card_body: WebElement):
    """
    Note that a page is available to read before calling this function.
    :param card_body: A card body object.
    :type card_body: WebElement
    :return: A dict contains data.
    :rtype: dict
    """
    # 左侧
    job_card_left = card_body.find_element(By.CLASS_NAME, 'job-card-left')
    # 左侧元素
    job_title = job_card_left.find_element(By.CLASS_NAME, 'job-title.clearfix')
    job_info = job_card_left.find_element(By.CLASS_NAME, 'job-info.clearfix')
    # 左侧元素里的数据
    data_job_name = job_title.find_element(By.CLASS_NAME, 'job-name').text  # 岗位名称
    data_job_area = job_title.find_element(By.CLASS_NAME, 'job-area-wrapper'). \
        find_element(By.CLASS_NAME, 'job-area').text
    data_salary = job_info.find_element(By.CLASS_NAME, 'salary').text
    data_tag_list = job_info.find_element(By.CLASS_NAME, 'tag-list').text

    # 右侧
    job_card_right = card_body.find_element(By.CLASS_NAME, 'job-card-right')
    # 右侧元素
    company_info = job_card_right.find_element(By.CLASS_NAME, 'company-info')
    # 右侧元素里的数据
    data_company_name = company_info.find_element(By.CLASS_NAME, 'company-name').text
    data_company_tag_list = company_info.find_element(By.CLASS_NAME, 'company-tag-list').text

    card_body_dict = {
        'job_name': data_job_name,
        'job_area': data_job_area,
        'salary': data_salary,
        'tag_list': data_tag_list,
        'company_name': data_company_name,
        'company_tag_list': data_company_tag_list
    }

    print(card_body_dict)

    return card_body_dict


def start():
    collect_data = CollectData()
    # collect_data.get_occupation_link_list()
    #
    # print(collect_data.occupation_links_list)
    #
    # # 打开一个链接
    # link = collect_data.occupation_links_list[0]

    # cookies = joblib.load('./cookies.pkl')
    # collect_data.driver.add_cookie(cookies)

    collect_data.driver.get("https://www.liepin.com/zhaopin/?d_sfrom=search_sub_site&key=Java&imscid=R000000035")

    time.sleep(5)
    # cookies = collect_data.driver.get_cookies()
    # print(cookies)
    # joblib.dump(cookies, 'cookies.pkl')

    # collect_data.get_job_cards_from_one_page()  # 收集cards
    # card = collect_data.job_cards_list_for_one_page[0]
    #
    # get_info_from_one_card(card)

    # for i in range(0, 100):
    #     options_page = collect_data.driver.find_element(By.CLASS_NAME, 'options-pages')
    #     next_page = options_page.find_elements(By.TAG_NAME, 'a')[-1]
    #     next_page.click()
    #     time.sleep(5)

    for i in range(0, 100):
        next_page = collect_data.driver.find_element(By.CLASS_NAME, 'ant-pagination-next')
        next_page.click()
        collect_data.driver.delete_all_cookies()
        time.sleep(10)

    collect_data.driver.close()


if __name__ == '__main__':
    start()
