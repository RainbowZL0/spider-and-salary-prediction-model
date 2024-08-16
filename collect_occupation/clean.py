import os
import pandas as pd

def get_files_in_folder(folder_path):
    file_paths = []
    for root, directories, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    return file_paths


def start():
    # 指定要遍历的文件夹路径
    folder_path = "./OUTPUT_FOLDER"

    # 调用函数获取文件路径列表
    file_paths = get_files_in_folder(folder_path)

    length = 0
    # 打印文件路径列表
    for path in file_paths:
        new_df = pd.read_excel(path)
        length += len(new_df)
    print(length)


if __name__ == '__main__':
    start()
