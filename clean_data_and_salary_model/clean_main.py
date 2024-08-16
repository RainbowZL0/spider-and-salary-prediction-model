import os
import pickle
import re
import textwrap
from clean_city2province_generate_dict import generate_province_dict
import numpy as np
import pandas as pd
from colorama import Fore, init
from holoviews.ipython import display

FILE_PATH = 'tables/拉勾招聘网06-28-1.xls'
FOLDER_PATH = 'tables'
KEYWORDS = ['运维', '测试', 'Java', 'Python', 'C++', '前端', '策划', '运营', '算法', '产品经理', '网络', 'linux',
            '嵌入式', '数据库', '信息安全', '人工智能', '软件服务']
init(autoreset=True)


class DataCleaning:
    def __init__(self):
        self.dataframe = None

    def show_excel(self):
        display(self.dataframe.to_string())
        self.dataframe.info()

    def show_duplicates(self):
        print("num of duplicated rows:")
        i = self.dataframe.duplicated().sum()
        print(i)
        print(self.dataframe[self.dataframe.duplicated(keep=False)])

    def drop_duplicates(self):
        self.dataframe.drop_duplicates(keep="first", inplace=True)
        self.dataframe.reset_index(inplace=True, drop=True)

    def show_rows_with_null(self, column_name):
        print(self.dataframe[pd.isnull(self.dataframe[column_name])])

    def drop_rows_with_null(self, column_name):
        return self.dataframe.dropna(axis=0, how='any', subset=[column_name], inplace=True)

    def string_format(self):
        """
        Clean the format for all the columns.
        """
        self.dataframe.loc[:, '公司'] = [str(x)[2:len(x) - 2] for x in self.dataframe.loc[:, '公司']]
        self.clean_column_payment()
        self.clean_column_experience()
        self.clean_places()

        # with open("city2province.pkl", "rb") as file:
        #     city2province = pickle.load(file, encoding='latin1')
        #     self.dataframe.loc[:, '工作地点'] = [str(x).split('·')[0].strip("[]") for x in self.dataframe.loc[:, '工作地点']]
        #     self.dataframe.loc[:, '工作地点'] = [city2province[x] + "-" + str(x) for x in self.dataframe.loc[:, '工作地点']]

        return self.dataframe

    def clean_places(self):
        # 修改城市列。列名为"工作地点"。
        self.dataframe.loc[:, '工作地点'] = [str(x).split('·')[0].strip("[]") for x in
                                             self.dataframe.loc[:, '工作地点']]

        # 添加省列。列名为"工作地点省"
        with open("city2province.pkl", "rb") as file:
            city2province = pickle.load(file, encoding='latin1')
            province_list = list()
            for city in self.dataframe["工作地点"]:
                province = city2province[city]
                province_list.append(province)
            province_array = np.array(province_list)

            insert_column_location = self.dataframe.columns.get_loc("工作地点")
            self.dataframe.insert(insert_column_location, "工作地点省", province_array)

    def read_excels_from_folder(self):
        """
        Read xls files from a folder. Join them together as a whole dataframe.
        return: pd.DataFrame
        """
        if not os.path.exists(FOLDER_PATH):
            print(Fore.RED + "Input folder does not exist.")
            exit()

        # Make a dataframe from all the xls tables.
        self.dataframe = pd.DataFrame(
            columns=["职位", "公司", "薪水", "学历要求", "工作经验", "工作地点", "标签"])
        file_name_list = os.listdir(FOLDER_PATH)
        for file_name in file_name_list:
            file_path = os.path.join(FOLDER_PATH, file_name)
            new_dataframe = pd.read_excel(file_path)
            self.dataframe = pd.concat([self.dataframe, new_dataframe], ignore_index=True)

    def drop_duplicated_rows_v2(self):
        """
        Exclude the last column because of the given instruction.
        """
        subset = ["职位", "公司", "薪水", "学历要求", "工作经验", "工作地点"]
        self.dataframe.drop_duplicates(subset=subset, inplace=True)

    def clean_column_payment(self):
        """
        Extract the min and max for every row.
        Form 2 columns to replace the original payment column.
        """
        payment_column = self.dataframe["薪水"]
        min_value_list = list()
        max_value_list = list()

        for index in payment_column.index:
            value = payment_column[index]
            value = value.replace("k", "000")
            value_split = value.split("-")
            min_value, max_value = value_split[0], value_split[1]
            min_value, max_value = int(min_value), int(max_value)
            min_value_list.append(min_value)
            max_value_list.append(max_value)

        # When exit the loop, the 2 lists are ready.
        # Next, remove the original payment column and insert new ones.
        column_location = self.dataframe.columns.get_loc("薪水")
        del self.dataframe["薪水"]

        min_value_ndarray = np.array(min_value_list)  # Convert data type.
        max_value_ndarray = np.array(max_value_list)
        self.dataframe.insert(column_location, "最大薪水", max_value_ndarray)
        self.dataframe.insert(column_location, "最小薪水", min_value_ndarray)

    def clean_column_experience(self):
        """
        Split the column to 2 pieces, which are min and max that suggests an interval.
        If any side of the interval is infinite, it will be assigned as -1.
        """
        INFINITE_VALUE = -1

        experience_column = self.dataframe["工作经验"]

        min_value_list, max_value_list = list(), list()
        for index, value in experience_column.items():
            value = value[2:]  # Remove "经验" in the first place.
            value = value.replace(" ", "")
            if "-" in value:
                value = value[:-1]  # Remove the last letter "年"
                min_max_list = value.split("-")
                min_value, max_value = min_max_list[0], min_max_list[1]
                min_value, max_value = int(min_value), int(max_value)
            elif value[-2:] == "不限":  # In other cases, consider the last several letters.
                min_value, max_value = INFINITE_VALUE, INFINITE_VALUE
            elif value[-3:] == "年以上":
                value = value[0:-3]
                min_value = int(value)
                max_value = INFINITE_VALUE
            elif value[-3:] == "年以下":
                value = value[0:-3]
                min_value = INFINITE_VALUE
                max_value = int(value)
            elif value == "在校":
                min_value, max_value = INFINITE_VALUE, INFINITE_VALUE
                print(Fore.RED + f"有工作经验'在校'的数据出现。row index = {index + 2}")
            else:
                min_value, max_value = INFINITE_VALUE, INFINITE_VALUE
                print(Fore.RED + f"有工作经验无法处理的数据出现。row index = {index}")
            # Finally add them to lists.
            min_value_list.append(min_value)
            max_value_list.append(max_value)
        # Loop is done up to now.

        # Remove the original experience column.
        # Convert lists to array and insert into the dataframe.
        column_location = self.dataframe.columns.get_loc("工作经验")
        del self.dataframe["工作经验"]

        min_value_ndarray = np.array(min_value_list)
        max_value_ndarray = np.array(max_value_list)
        self.dataframe.insert(column_location, "要求工作经验上限", max_value_ndarray)
        self.dataframe.insert(column_location, "要求工作经验下限", min_value_ndarray)

    def divide_work(self):
        self.dataframe['方向'] = self.dataframe.apply(find_keyword, axis=1)  # 应用find_keyword函数到每一行

    def handle_input(self):
        """
        Ensure that you choose 0 or 1 in the first time.
        Then choose available operations.
        """
        msg = textwrap.dedent(f"""
        {Fore.YELLOW}Please enter your request.{Fore.GREEN}
        0: Read one table from the given path.
        1: Read all containing tables from the folder path.
        2: Default Processing (recommend).
        3: Show excel.
        4: Show duplicates.
        5: Drop duplicates.
        6: String format.
        7: Show rows with null values.
        8: Drop rows with null values.
        9: City-province match.
        """)
        lines = input(msg)

        # Ensure that you input a dataframe first.
        while lines != 'q':
            if not (lines == '0' or lines == '1'):
                print(Fore.RED + "You have not input a dataframe yet. Try choice 0 or 1 first.")
                lines = input()
            else:
                break

        # Start operations
        while lines != 'q':
            if lines == '0':
                self.dataframe = pd.read_excel(FILE_PATH)
            elif lines == '1':
                self.read_excels_from_folder()
            elif lines == '2':
                self.drop_rows_with_null('学历要求')
                self.drop_duplicates()
                self.string_format()
                self.drop_duplicates()
                self.divide_work()
                self.dataframe.to_excel('output.xlsx', index=False)
            elif lines == '3':
                self.show_excel()
            elif lines == '4':
                self.show_duplicates()
            elif lines == '5':
                self.drop_duplicates()
                print("duplicates dropped\n")
            elif lines == '6':
                self.string_format()
            elif lines == '7':
                lines = input("please enter a column name\n")
                self.show_rows_with_null(lines)
            elif lines == '8':
                lines = input("please enter a column name\n")
                self.drop_rows_with_null(lines)
            elif lines == '9':
                print(1)
            elif lines == 'output':
                self.dataframe.to_excel('output.xlsx', index=False)
            else:
                print(Fore.RED + 'invalid request, please check and enter again\n')

            lines = input(msg)


def find_keyword(row):
    job_title = str(row['职位'])  # 将职位列转换为字符串
    job_tags = str(row['标签'])  # 将标签列转换为字符串
    text = job_title + job_tags  # 合并职位和标签字符串
    for keyword in KEYWORDS:
        # 创建忽略大小写的正则表达式对象
        # re.escape()会把正则式的关键符号当做普通字符匹配。例如[]()等。
        # re.compile()创建正则式对象
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        if pattern.search(text):
            return keyword
    return float('nan')


def start():
    cleaner = DataCleaning()
    cleaner.handle_input()


if __name__ == '__main__':
    generate_province_dict()
    start()
