import pandas as pd
import json

file = "/home/vinikuhlmann/Desktop/sigmine-dashboard/levantamento DMS_Empresas.xlsx"
grupos = {}
df = pd.read_excel(file)
for _, empresa, grupo in df.itertuples(index=False):
    grupos[empresa] = grupo

with open("grupos.json", "w") as f:
    json.dump(grupos, f, indent=4, ensure_ascii=False)
