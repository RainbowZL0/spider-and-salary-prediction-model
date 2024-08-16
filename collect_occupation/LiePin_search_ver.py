import time

import joblib
import pandas as pd
import selenium
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

PAGES = 10


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

        self.df = create_new_dataframe()

    def get_occupation_link_list(self):
        """
        获得各个行业的link list
        """
        self.driver.get("")

        # 鼠标移动到菜单上悬停
        menu = self.driver.find_element(By.XPATH, '//*[@id="main"]/div/div[1]/div/div[1]/dl[1]/dd')
        self.action.move_to_element(menu).perform()

        # class_name为text对应的是“后端开发”领域
        text = self.driver.find_element(By.CLASS_NAME, 'text')
        buttons = text.find_elements(By.TAG_NAME, 'a')
        for button in buttons:
            link = button.get_attribute('href')
            self.occupation_links_list.append(link)

    def collect_info_from_one_occupation(self):
        """

        :return:
        :rtype:
        """
        one_occupation_list = list()

        # 第1页的收集
        one_page_list = self.collect_info_from_one_page()
        one_occupation_list += one_page_list
        # 后续页的收集。总共PAGES页
        for i in range(1, PAGES):
            self.click_next_page()
            one_page_list = self.collect_info_from_one_page()
            one_occupation_list += one_page_list
            pass

        return one_occupation_list

    def collect_info_from_one_page(self):
        """
        获取一页的list(dict())，每个dict都是一个card的信息
        :return: one_page_list
        :rtype: list(dict())
        """
        self.get_job_cards_from_one_page()  # 把这一个page的card都准备好

        one_page_list = list()
        for card in self.job_cards_list_for_one_page:
            one_card_list = get_info_from_one_card(card)
            one_page_list.append(one_card_list)

        return one_page_list

    def get_job_cards_from_one_page(self):
        """
        Note that a page should be opened before calling this method.
        :return: job cards for one page
        :rtype: WebElement
        """
        job_list_box = self.driver.find_element(By.CLASS_NAME, 'job-list-box')
        elements_list = job_list_box.find_elements(By.TAG_NAME, 'div')

        # 从elements_list中筛选出job card
        cards_list = list()
        for element in elements_list:
            if element.get_attribute('style') == "margin-bottom: 10px;":
                cards_list.append(element)
        self.job_cards_list_for_one_page = cards_list

    def click_next_page(self):
        self.driver.delete_all_cookies()

        next_page_button = self.driver.find_element(By.CLASS_NAME, 'ant-pagination-next')
        next_page_button.click()

        time.sleep(2)

    def get_cookies(self):
        self.driver.get("https://www.liepin.com/")
        time.sleep(1)
        cookies = self.driver.get_cookies()
        joblib.dump(cookies, 'cookies.pkl')

    def load_cookies(self):
        cookies = joblib.load('cookies.pkl')
        for cookie in cookies:
            self.driver.add_cookie(cookie)
        self.driver.refresh()

    def login_in(self):
        switch_to_login_with_password = self.driver.find_element(
            By.CLASS_NAME,
            'jsx-3565815463.login-tabs-line-text'
        )
        switch_to_login_with_password.click()

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


def get_info_from_one_card(card: WebElement):
    """
    返回这一条招聘信息对应的dict
    :param card: 一条招聘信息的card
    :type card: WebElement
    :return: 一个dict
    :rtype: dict
    """
    card_compo_div = card.find_elements(By.TAG_NAME, 'div')

    job_name = card_compo_div[5].text
    job_place = card_compo_div[6].find_elements(By.TAG_NAME, 'span')[1].text
    salary = card_compo_div[3].find_elements(By.TAG_NAME, 'span')[-1].text
    work_exp, education, job_tags = prepare_job_tags(card_compo_div[7])

    company_name = card_compo_div[9].find_element(By.TAG_NAME, 'span').text
    company_tags = prepare_company_tags(card_compo_div[11])

    one_card_dict = {
        '职位': job_name,
        '公司': company_name,
        '薪水': salary,
        '学历要求': education,
        '工作经验': work_exp,
        '工作地点': job_place,
        '标签': job_tags,
        '公司标签': company_tags
    }

    return one_card_dict


def prepare_job_tags(div: WebElement):
    tags = div.find_elements(By.TAG_NAME, 'span')

    # 单独取出前两条，分别是工作经验和学历
    work_exp = tags[0].text
    education = tags[1].text
    tags = tags[2:]  # remove the first and the second

    # 处理其余的标签，join成一个长字符串，用$连接
    if len(tags) == 0:
        other_tags_str = ""
    else:
        tags_str_list = convert_to_str_list(tags)
        other_tags_str = '$'.join(tags_str_list)

    return work_exp, education, other_tags_str


def prepare_company_tags(div: WebElement):
    tags = div.find_elements(By.TAG_NAME, 'span')

    tags_str_list = convert_to_str_list(tags)
    tags_str = '$'.join(tags_str_list)

    return tags_str


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
    创建一个新的dataframe。因为复用次数太多了，只写一遍，以后调用这个函数即可。
    :return: 空dataframe
    :rtype: pd.DataFrame
    """
    return pd.DataFrame(columns=["职位", "公司", "薪水", "学历要求", "工作经验", "工作地点", "标签", "公司标签"])


def start():
    collect_data = CollectData()
    # collect_data.get_occupation_link_list()
    #
    # print(collect_data.occupation_links_list)
    #
    # # 打开一个链接
    # link = collect_data.occupation_links_list[0]

    collect_data.driver.get("https://www.liepin.com/")
    time.sleep(3)
    one_page_list = collect_data.collect_info_from_one_occupation()
    df = pd.DataFrame(one_page_list)
    df.to_excel('1.xlsx')

    collect_data.driver.close()


def cookie_test():
    collect_data = CollectData()
    collect_data.get_cookies()


if __name__ == '__main__':
    start()
    # cookie_test()
