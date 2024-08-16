import re

import pandas as pd
import colorama
from colorama import Fore

colorama.init(autoreset=True)


def dataframe_test():
    df = pd.DataFrame([[1, 2], [3, 4]], columns=list('AB'), index=['x', 'y'])
    df2 = pd.DataFrame([[5, 6], [7, 8]], columns=list('AB'), index=['x', 'y'])
    df3 = pd.concat([df, df2], ignore_index=True)

    print(df3)


def except_test():
    try:
        age = int(input("请输入你的年龄："))
        assert age >= 0, "年龄不能为负数。"
        assert age <= 120, "年龄不能大于120岁。"
        print("你的年龄是：", age)
    except Exception as e:
        print(f"{Fore.RED}发生了一个异常：{e}")


def test(func):
    func()


def k():
    print(2)


def a():
    print(1)


if __name__ == '__main__':
    pass
