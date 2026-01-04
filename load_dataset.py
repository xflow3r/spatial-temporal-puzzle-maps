import pandas as pd

# I found it easier to get the file paths right, when there is a dedicated method for loading the dataset
def load_dataset(print_dataset=False):
    df = pd.read_csv('United_States_Cancer_Statistics_1999_to_2021_Mortality.csv')

    if print_dataset:
        print(df.to_string())

    return df


if __name__ == '__main__':
    load_dataset(True)