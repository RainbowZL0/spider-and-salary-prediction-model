import pickle

'''
    make cities-to-province dictionary and save as city2province.pkl file
'''


def generate_province_dict():
    city2province = {}
    filename = "city2province.pkl"
    txt = open('./city-province.txt', encoding='UTF-8')
    line = txt.readline()
    while line:
        line = txt.readline()
        split_line = line.strip('\n').split(' ')
        value = split_line[0]
        for seg in split_line:
            city2province[seg] = value
    print(city2province)
    with open(filename, "wb") as file:
        pickle.dump(city2province, file)
    txt.close()


if __name__ == '__main__':
    generate_province_dict()
