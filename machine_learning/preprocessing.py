import pandas as pd

file_path = 'machine_learning\dataset.csv'

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

df = pd.read_csv(file_path)

print(df.head(10))