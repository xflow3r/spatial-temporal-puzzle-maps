import pandas as pd

def load_dataset(print_dataset=False):
    df = pd.read_csv("United_States_Cancer_Statistics_1999_to_2021_Mortality.csv")

    if print_dataset:
        print(df.head().to_string())

    # --- CHANGE THESE if your CSV uses different names ---
    year_col = "Year"
    deaths_col = "Deaths"   # or "Death Count", etc.
    # -----------------------------------------------------

    # Group by state + code, then build year->deaths map
    grouped = (
        df.groupby(["State", "State_numerical"])[[year_col, deaths_col]]
          .apply(lambda g: dict(zip(g[year_col], g[deaths_col])))
          .reset_index(name="deaths_by_year")
    )

    return grouped.to_dict(orient="records")

if __name__ == "__main__":
    data = load_dataset()
    print(data[0])  # show first "object"
