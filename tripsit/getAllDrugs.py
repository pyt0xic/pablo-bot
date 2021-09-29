import requests, json
import pandas as pd

# API URL
url = "http://tripbot.tripsit.me/api/tripsit/getAllDrugs"
r = requests.get(url)
data = r.json()

# Format dict and load into df
data = json.dumps(data["data"][0], indent=2, sort_keys=False, ensure_ascii=False)
df = pd.DataFrame.from_dict(json.loads(data), orient="index")

# Add id for each drug for rasa
id = []
for x in range(0, len(df)):
    id.append(x)
df["id"] = id

# Write to JSON file
with open("tripsit/getAllDrugs.json", "w") as fp:
    # Clean NaN values
    clean_data = {
        k1: {k: v for k, v in v1.items() if v == v and v is not None}
        for k1, v1 in df.to_dict("index").items()
    }
    # Set ensure_ascii to false to ensure we can keep greek letters (like alpha)
    fp.write(json.dumps(clean_data, indent=2, ensure_ascii=False))
