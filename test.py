import gzip
import pandas as pd


filepath = r"mimic-iv-clinical-database-demo-1.0\mimic-iv-clinical-database-demo-1.0\hosp\emar.csv.gz"
# with open(filepath, "rb") as f:
#     print(f.readlines()[0])

# print(filepath)

df = pd.read_csv(filepath)
print(df.head())