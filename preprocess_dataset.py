import pandas as pd

def load_dataset(print_dataset=False, save_processed=True):
    df_cancer = pd.read_csv("cancerData/United_States_Cancer_Statistics_1999_to_2021_Mortality.csv")
    df_population = pd.read_csv("cancerData/Population_by_state_and__year.csv")

    df_cancer = df_cancer[(df_cancer["Year"] > 2004) & (df_cancer["Year"] <= 2020)]
    df_population = df_population[
        (df_population["Year"] > 2004) & (df_population["Year"] <= 2020)
    ]

    deaths_by_year = (
        df_cancer
        .groupby(["State", "State_numerical", "Year"], as_index=False)
        ["Deaths"]
        .sum()
    )

    population_by_year = (
        df_population
        .groupby(["State", "State_numerical", "Year"], as_index=False)
        ["Population"]
        .sum()
    )

    df = pd.merge(
        deaths_by_year,
        population_by_year,
        on=["State", "State_numerical", "Year"],
        how="inner"
    )

    df["death_rate_per_100k"] = (df["Deaths"] / df["Population"]) * 100000

    grouped = (
        df.groupby(["State", "State_numerical"])
        .apply(lambda g: {
            "deaths_by_year": dict(zip(g["Year"], g["Deaths"])),
            "population_by_year": dict(zip(g["Year"], g["Population"])),
            "death_rate_by_year": dict(zip(g["Year"], g["death_rate_per_100k"]))
        }, include_groups=False)
        .reset_index(name="metrics")
    )

    if save_processed:
        df.to_csv("cancerData/cancer_data_2004_2020.csv", index=False)

    if print_dataset:
        print(df.head().to_string())

    return grouped.to_dict(orient="records")


if __name__ == "__main__":
    data = load_dataset(True, False)
    print(data[0])  # show first "object"
