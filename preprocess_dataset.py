import pandas as pd

def load_dataset(print_dataset=False, save_processed=True):
    df = pd.read_csv("cancerData/United_States_Cancer_Statistics_1999_to_2021_Mortality.csv")

    if print_dataset:
        print(df.head().to_string())

    # Filter to 2004-2020 only
    df = df[(df["Year"] >= 2004) & (df["Year"] <= 2020)]

    if save_processed:
        df.to_csv("cancerData/cancer_data_2004_2020.csv", index=False)

    # Group by state + code, then build year -> deaths map
    grouped = (
        df.groupby(["State", "State_numerical"])[["Year", "Deaths"]]
          .apply(lambda g: dict(zip(g["Year"], g["Deaths"])))
          .reset_index(name="deaths_by_year")
    )

    return grouped.to_dict(orient="records")

if __name__ == "__main__":
    data = load_dataset()
    print(data[0])  # show first "object"
