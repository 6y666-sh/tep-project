import pyreadr
import pandas as pd

RAW = "data/raw"
PROCESSED = "data/processed"

files = {
    "fault_free_training": "TEP_FaultFree_Training",
    "fault_free_testing": "TEP_FaultFree_Testing",
    "faulty_training": "TEP_Faulty_Training",
    "faulty_testing": "TEP_Faulty_Testing",
}

for out_name, fname in files.items():
    result = pyreadr.read_r(f"{RAW}/{fname}.RData")
    df = result[list(result.keys())[0]]
    df.to_parquet(f"{PROCESSED}/{out_name}.parquet", index=False)
    print(out_name, df.shape, "저장 완료")