import colorama
import joblib
import pandas as pd
from colorama import Fore
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

IS_TRAINING_MODE = False
FILE_PATH = "output.xlsx"
HAS_WEIGHTS_AVG = True

colorama.init(autoreset=True)


class SalaryModel:
    def __init__(self):
        self.df = pd.read_excel(FILE_PATH)

        # in order to convert the features to numbers that are readable to the computer.
        self.column_trans = ColumnTransformer(
            [('one_hot', OneHotEncoder(), ['学历要求', '工作地点'])],
            remainder='passthrough'
        )

        # all training sets
        self.X_train = None
        self.y_min_train = None
        self.y_max_train = None

        # all test sets
        self.X_test = None
        self.y_min_test = None
        self.y_max_test = None

        # 2 models that are used to predict the min salary and the max salary
        self.min_model = RandomForestRegressor(n_estimators=200)
        self.max_model = RandomForestRegressor(n_estimators=200)

        # new X features that will be used to predict the salary
        self.X_new = None

        # predicted salary comes from an avg with weights
        self.avg_weight_counter: dict = dict()

    def preprocess(self):
        """
        Complete all the preprocessing operations for the training and test datasets.
        """
        # features and results
        X_df = self.df[["学历要求", "工作地点", "要求工作经验下限"]]
        min_salary_df = self.df["最小薪水"]
        max_salary_df = self.df["最大薪水"]

        # encode
        X_encoded = self.column_trans.fit_transform(X_df)

        # split the set to form a training set and a test set
        self.X_train, self.X_test, self.y_min_train, self.y_min_test = train_test_split(X_encoded,
                                                                                        min_salary_df,
                                                                                        test_size=0.2,
                                                                                        random_state=42)
        _, _, self.y_max_train, self.y_max_test = train_test_split(X_encoded,
                                                                   max_salary_df,
                                                                   test_size=0.2,
                                                                   random_state=42)
        self.count_work_exp_for_avg_weights()

    def count_work_exp_for_avg_weights(self):
        """
        Will be utilized to serve as weights for computing avg.
        :return: counter
        :rtype: dict
        """
        min_exp_column = self.df["要求工作经验下限"]

        counter = {
            -1: 0,
            1: 0,
            3: 0,
            5: 0,
            10: 0
        }
        for element in min_exp_column:
            counter[element] += 1

        # assert the number of count matches the rows
        try:
            num_of_rows = 0
            for value in counter.values():
                num_of_rows += value
            assert num_of_rows == len(min_exp_column), "Count does not match the number of rows"
        except AssertionError as e:
            print(f"{Fore.RED}An error occurred. {e}")

        # # convert to rates that represent portions
        # for index, value in counter.items():
        #     value = value / len(min_exp_column)
        #     counter[index] = value

        self.avg_weight_counter = counter

    def train_models(self):
        """
        Train 2 models
        """
        self.min_model.fit(self.X_train, self.y_min_train)
        self.max_model.fit(self.X_train, self.y_max_train)

    def validate_models(self):
        """
        Validate 2 models
        """
        y_min_prediction = self.min_model.predict(self.X_test)
        y_max_prediction = self.max_model.predict(self.X_test)

        # calculate loss
        y_min_MAE = mean_absolute_error(y_min_prediction, self.y_min_test)
        y_max_MAE = mean_absolute_error(y_max_prediction, self.y_max_test)

        print(f"Mean Absolute Error for Min Salary: {Fore.RED}{y_min_MAE}")
        print(f"Mean Absolute Error for Max Salary: {Fore.RED}{y_max_MAE}")

    def make_predictions(self):
        """
        Make predictions with weights or not.
        :return: result as an interval
        :rtype: str
        """
        if HAS_WEIGHTS_AVG:
            min_prediction = self.make_predictions_by_avg(self.min_model)
            max_prediction = self.make_predictions_by_avg(self.max_model)
        else:
            X_new_encoded = self.column_trans.transform(self.X_new)
            min_prediction = self.min_model.predict(X_new_encoded)[0]
            max_prediction = self.max_model.predict(X_new_encoded)[0]

        # Reformat. Keep 2 decimal digits. Convert to str as an interval.
        min_prediction, max_prediction = round(min_prediction, 2), round(max_prediction, 2)
        result = f"{str(min_prediction)}-{str(max_prediction)}"

        return result

    def make_predictions_by_avg(self, given_model):
        """
        Compute the avg salary with weights.
        :param given_model: min or max model
        :type given_model: RandomForestRegressor
        :return: avg_salary
        :rtype: float
        """
        work_exp = self.X_new["要求工作经验下限"][0]
        floor_work_exp = get_floor_work_exp(work_exp)

        if floor_work_exp == 1:
            # total num of concerned rows
            sum_num = 0
            for index, num in self.avg_weight_counter.items():
                if index <= floor_work_exp:
                    sum_num += num
                else:
                    break

            avg_salary = 0
            X_new_copy = self.X_new.copy()
            for index, num in self.avg_weight_counter.items():
                if index <= floor_work_exp:
                    X_new_copy.loc[0, "要求工作经验下限"] = index
                    X_new_encoded = self.column_trans.transform(X_new_copy)
                    prediction_array = given_model.predict(X_new_encoded)

                    ratio = num / sum_num
                    predicted_salary = prediction_array[0] * ratio

                    avg_salary += predicted_salary
                else:
                    break
        else:
            X_new_encoded = self.column_trans.transform(self.X_new)
            avg_salary = given_model.predict(X_new_encoded)[0]

        return avg_salary


def get_floor_work_exp(years):
    """
    Minimize the work exp to the lower value.
    :param years: work exp got in the past
    :type years: int
    :return: floored time span
    :rtype: int
    """
    try:
        assert 0 <= years, "Work experience should be greater than 0"
    except AssertionError as e:
        print(f"{Fore.RED}An error occurred. {e}")

    if 10 <= years:
        years = 10
    elif 5 <= years < 10:
        years = 5
    elif 3 <= years < 5:
        years = 3
    elif 1 <= years < 3:
        years = 1
    else:
        years = 0

    return years


def start_training():
    salary_model = SalaryModel()
    salary_model.preprocess()
    salary_model.train_models()
    salary_model.validate_models()
    joblib.dump(salary_model, "salary_model.pkl")


def start_predicting(qualification, city, work_exp):
    test_model: SalaryModel = joblib.load("salary_model.pkl")

    # convert types
    qualification = str(qualification)
    city = str(city)
    work_exp = int(work_exp)

    test_model.X_new = pd.DataFrame({
        "学历要求": [qualification],
        "工作地点": [city],
        "要求工作经验下限": [work_exp]
    })
    result = test_model.make_predictions()

    return result


def start():
    if IS_TRAINING_MODE:
        start_training()
    else:
        start_predicting(qualification="本科",
                         city="北京",
                         work_exp="1")


# if __name__ == '__main__':
#     start()
