import pandas as pd
import os, json

# Generates metadata of the dataset (e.g. number of rows, names of columns, etc.)

folderpath_mimic_iv = r"mimic-iv-clinical-database-demo-2.2\mimic-iv-clinical-database-demo-2.2"
dict_metadata = {}

for item in os.scandir(folderpath_mimic_iv):
    if item.is_dir():
        modulename = os.path.basename(item.path)
        dict_metadata[modulename] = {}
        for filename in os.listdir(item):
            tablename = filename.split(".")[0]
            df = pd.read_csv(os.path.join(item.path, filename), low_memory=False)
            n_rows = len(df.index)
            dict_metadata[modulename][tablename] = {
                "n_rows": n_rows,
                "columns": {
                    "colname": df.columns.tolist(),
                    "dtype": [str(dtype) for dtype in df.dtypes]
                }
            }
            
with open("dataset_metadata.json", "w") as f:
    json.dump(dict_metadata, f, indent=4)