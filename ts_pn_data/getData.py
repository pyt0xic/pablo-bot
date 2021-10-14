"""MIT License

Copyright (c) 2021 Noah Saso

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

#!/usr/bin/env python3

# downloads and exports data on all substances from psychonautwiki and tripsit factsheets, combining to form master list with standardized format
# prioritizes psychonautwiki ROA info (dose/duration) over tripsit factsheets
# pip3 install beautifulsoup4 requests python-graphql-client

import requests
from bs4 import BeautifulSoup
from python_graphql_client import GraphqlClient
import json
import os
import re
import traceback
from TrainingDataGen import DataGen

headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "3600",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0",
}

ts_api_url = "https://tripbot.tripsit.me/api/tripsit/getAllDrugs"
ps_api_url = "https://api.psychonautwiki.org"
ps_client = GraphqlClient(endpoint=ps_api_url, headers=headers)


def substance_name_match(name, substance):
    """check if name matches any value in keys we care about"""
    lower_name = name.lower()
    return any(
        [
            lower_name == substance[key].lower()
            for key in ["name", "pretty_name"]
            if key in substance
        ]
        + [lower_name == alias.lower() for alias in substance.get("aliases", [])]
    )


def find_substance_in_data(data, name):
    return next((s for s in data if substance_name_match(name, s)), None)


roa_name_aliases = {
    "iv": ["intravenous"],
    "intravenous": ["iv"],
    "im": ["intramuscular"],
    "intramuscular": ["im"],
    "insufflated": ["snorted"],
    "snorted": ["insufflated"],
    "vaporized": ["vapourized"],
    "vapourized": ["vaporized"],
}


def roa_matches_name(roa, name):
    aliases = roa_name_aliases.get(name.lower(), [])
    return roa["name"].lower() == name.lower() or roa["name"].lower() in aliases


# get tripsit data


ts_dose_order = ["Threshold", "Light", "Common", "Strong", "Heavy"]
ts_combo_ignore = ["benzos"]  # duplicate
# prettify names in interaction list
ts_combo_transformations = {
    "lsd": "LSD",
    "mushrooms": "Mushrooms",
    "dmt": "DMT",
    "mescaline": "Mescaline",
    "dox": "DOx",
    "nbomes": "NBOMes",
    "2c-x": "2C-x",
    "2c-t-x": "2C-T-x",
    "amt": "aMT",
    "5-meo-xxt": "5-MeO-xxT",
    "cannabis": "Cannabis",
    "ketamine": "Ketamine",
    "mxe": "MXE",
    "dxm": "DXM",
    "pcp": "PCP",
    "nitrous": "Nitrous",
    "amphetamines": "Amphetamines",
    "mdma": "MDMA",
    "cocaine": "Cocaine",
    "caffeine": "Caffeine",
    "alcohol": "Alcohol",
    "ghb/gbl": "GHB/GBL",
    "opioids": "Opioids",
    "tramadol": "Tramadol",
    "benzodiazepines": "Benzodiazepines",
    "maois": "MAOIs",
    "ssris": "SSRIs",
}

ts_response = requests.get(ts_api_url)
ts_data = ts_response.json()["data"][0]

ts_substances_data = list(ts_data.values())


# TS has durations split over a few keys, so this finds or creates the duration for the associated ROA
# and adds a new line item
def ts_add_formatted_duration(ts_roas, formatted_duration, duration_name):
    units = formatted_duration.get("_unit", "") or ""
    if "_unit" in formatted_duration:
        formatted_duration.pop("_unit")

    def add_to_roa(roa, value):
        if "duration" not in roa:
            roa["duration"] = []

        roa["duration"].append({"name": duration_name, "value": value})

    for roa_name, value in formatted_duration.items():
        value_string = f"{value} {units}".strip()

        # if value present (i.e. just one value for all ROA doses provided above), apply to all ROAs
        if roa_name == "value":
            # if TS did not add any doses, do nothing with this value
            # we could theoretically apply this to all PW doses with missing durations, but we can't be sure
            # if it applies to all ROAs, so just ignore
            if not len(ts_roas):
                break

            for ts_roa in ts_roas:
                add_to_roa(ts_roa, value_string)

        # add to matching ROA or create new ROA if doesn't exist
        else:
            ts_roa = next(
                (ts_roa for ts_roa in ts_roas if roa_matches_name(ts_roa, roa_name)),
                None,
            )
            # if ROA doesn't exist, make new
            if not ts_roa:
                ts_roa = {"name": roa_name}
                ts_roas.append(ts_roa)

            add_to_roa(ts_roa, value_string)


# get psychonautwiki data


def pw_clean_common_name(name):
    name = re.sub(r'^"', "", name)
    name = re.sub(r'"$', "", name)
    name = re.sub(r'"?\[\d*\]$', "", name)
    name = re.sub(r"\s*More names\.$", "", name)
    name = re.sub(r"\.$", "", name)
    name = re.sub(r"\(.*\)", "", name)
    return name.strip()


def pw_should_skip(name, soup):
    return (
        name.startswith("Experience:") or len(soup.find_all(text="Common names")) == 0
    )


pw_substance_data = []

if os.path.exists("ts_pn_data/_cached_pw_substances.json"):
    with open("ts_pn_data/_cached_pw_substances.json") as f:
        pw_substance_data = json.load(f)

if not len(pw_substance_data):
    pw_substance_urls_query = """
    {
        substances(limit: 11000) {
            name
            url
        }
    }
    """

    pw_substance_urls_data = ps_client.execute(query=pw_substance_urls_query)["data"][
        "substances"
    ]

    for idx, substance in enumerate(pw_substance_urls_data):
        try:
            url = substance["url"]
            substance_req = requests.get(url, headers)
            substance_soup = BeautifulSoup(substance_req.content, "html.parser")

            name = substance_soup.find("h1", id="firstHeading").text
            if pw_should_skip(name, substance_soup):
                print(f"Skipping {name} ({idx + 1} / {len(pw_substance_urls_data)})")
                continue

            # get aliases text
            common_names_str = substance_soup.find_all(text="Common names")

            cleaned_common_names = (
                set(
                    map(
                        pw_clean_common_name,
                        common_names_str[0]
                        .parent.find_next_sibling("td")
                        .text.split(", "),
                    )
                )
                if len(common_names_str) > 0
                else set()
            )
            cleaned_common_names.add(substance["name"])
            print(cleaned_common_names)
            # don't include name in list of other common names
            common_names = sorted(filter(lambda n: n != name, cleaned_common_names))

            # scrape ROAs from page

            def get_data_starting_at_row(curr_row):
                rows = []
                while curr_row.find("th", {"class": "ROARowHeader"}):
                    row = {}
                    row["name"] = (
                        curr_row.find("th", {"class": "ROARowHeader"}).find("a").text
                    )

                    row_values = curr_row.find("td", {"class": "RowValues"})

                    row_value_text = row_values.find_all(text=True, recursive=False)
                    if len(row_value_text):
                        row["value"] = "".join(row_value_text).strip()
                    else:
                        row["value"] = None

                    row_note = row_values.find("span")
                    if row_note:
                        row["note"] = re.sub(r"\s*\[\d*\]$", "", row_note.text).strip()

                    rows.append(row)

                    curr_row = curr_row.find_next("tr")
                return rows, curr_row

            roas = []

            dose_charts = substance_soup.find_all("tr", {"class": "dosechart"})
            for dose_chart in dose_charts:
                table = dose_chart.parent.parent
                roa_name = table.find("tr").find("a").text
                if not roa_name:
                    continue

                roa = {
                    "name": roa_name,
                    "dosage": [],
                    "duration": [],
                }

                # dosage

                curr_row = dose_chart.find_next("tr")
                roa["dosage"], curr_row = get_data_starting_at_row(curr_row)

                # extract bioavailability
                if len(roa["dosage"]) and roa["dosage"][0]["name"] == "Bioavailability":
                    bioavailability = roa["dosage"].pop(0)
                    roa["bioavailability"] = bioavailability["value"]

                # duration

                if curr_row.find("th", {"class": "ROASubHeader"}):
                    curr_row = curr_row.find_next("tr")
                    roa["duration"], _ = get_data_starting_at_row(curr_row)

                if not len(roa["dosage"]):
                    roa["dosage"] = None
                if not len(roa["duration"]):
                    roa["duration"] = None

                roas.append(roa)

            # query PS API for more data on substance

            query = (
                """
                {
                    substances(query: "%s") {
                        name
                        class {
                            chemical
                            psychoactive
                        }
                        tolerance {
                            full
                            half
                            zero
                        }
                        toxicity
                        addictionPotential
                        crossTolerances
                    }
                }
            """
                % substance["name"]
            )

            data = ps_client.execute(query=query)["data"]["substances"]
            if len(data) == 0:
                continue
            elif len(data) > 1:
                # should never happen?
                print(f"{name} has more than one dataset... investigate why")

            data = data[0]
            if "name" in data:
                data.pop("name")

            pw_substance_data.append(
                {
                    "url": url,
                    "name": name,
                    "aliases": common_names,
                    "roas": roas,
                    "data": data,
                }
            )
            print(
                f"Done with {name} [{len(roas)} ROA(s)] ({idx + 1} / {len(pw_substance_urls_data)})"
            )

        except KeyboardInterrupt:
            print("\nScrape canceled")
            exit(0)
        except:
            print(f"{name} failed:")
            print(traceback.format_exc())
            exit(1)

    with open(f"ts_pn_data/_cached_pw_substances.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(pw_substance_data, indent=2, ensure_ascii=False))

# combine tripsit and psychonautwiki data


all_substance_names = sorted(
    set(
        list(map(lambda s: s.get("name", "").lower(), pw_substance_data))
        + list(map(lambda s: s.get("name", "").lower(), ts_substances_data))
    )
)
substance_data = []
x = 0

for name in all_substance_names:
    # find PW substance
    pw_substance = find_substance_in_data(pw_substance_data, name)
    # remove to get rid of duplicates in final output
    if pw_substance:
        pw_substance_data.remove(pw_substance)
    else:
        pw_substance = {}

    # find TS substance
    ts_substance = find_substance_in_data(ts_substances_data, name)
    # remove to get rid of duplicates in final output
    if ts_substance:
        ts_substances_data.remove(ts_substance)
    else:
        ts_substance = {}

    # if no substance found in either dataset, skip
    if not pw_substance and not ts_substance:
        continue

    ts_properties = ts_substance.get("properties", {})

    # url will always exist for psychonautwiki substance, so tripsit substance must exist if url is None
    url = pw_substance.get("url") or f"https://drugs.tripsit.me/{ts_substance['name']}"

    ts_links = ts_substance.get("links", {})
    experiences_url = ts_links.get("experiences")

    # pick display name from available substances found from both datasets
    names = list(
        filter(
            lambda n: n is not None and len(n) > 0,
            [pw_substance.get("name"), ts_substance.get("pretty_name")],
        )
    )
    # people use shorter names
    name = min(names, key=len)

    # lowercase list of all names, excluding chosen name above
    aliases = set(
        map(
            lambda n: n.lower(),
            filter(
                lambda n: n is not None and len(n) > 0,
                [pw_substance.get("name"), ts_substance.get("pretty_name")]
                + pw_substance.get("aliases", [])
                + ts_substance.get("aliases", []),
            ),
        )
    )
    if name.lower() in aliases:
        aliases.remove(name.lower())
    aliases = sorted(aliases)

    summary = ts_properties.get("summary", "").strip()
    if not len(summary):
        summary = None

    test_kits = ts_properties.get("test-kits", "").strip()
    if not len(test_kits):
        test_kits = None

    ts_bioavailability_str = ts_properties.get("bioavailability", "").strip()
    ts_bioavailability = {}
    if len(ts_bioavailability_str):
        matches = re.findall(
            r"([a-zA-Z\/]+)[.:\s]+([0-9\.%\s\+/\-]+)", ts_bioavailability_str
        )
        if len(matches):
            for roa_name, value in matches:
                ts_bioavailability[roa_name.lower()] = value.strip(". \t")

    pw_data = pw_substance.get("data", {})

    classes = pw_data.get("class")
    toxicity = pw_data.get("toxicity")
    addiction_potential = pw_data.get("addictionPotential")
    tolerance = pw_data.get("tolerance")
    cross_tolerances = pw_data.get("crossTolerances")

    roas = []

    # get PW ROAs
    pw_roas = pw_substance.get("roas", [])

    # process TS ROAs
    ts_roas = []

    # TS ROA dosage
    ts_formatted_dose = ts_substance.get("formatted_dose")
    if ts_formatted_dose:
        for roa_name, dose_data in ts_formatted_dose.items():
            dose_levels = []
            for dose_level in ts_dose_order:
                value_string = dose_data.get(dose_level)
                if value_string is None:
                    continue

                dose_levels.append(
                    {
                        "name": dose_level,
                        "value": value_string,
                    }
                )

            if len(dose_levels):
                ts_roas.append({"name": roa_name, "dosage": dose_levels})

    # TS ROA durations
    ts_formatted_onset = ts_substance.get("formatted_onset")
    if ts_formatted_onset:
        ts_add_formatted_duration(ts_roas, ts_formatted_onset, "Onset")

    ts_formatted_duration = ts_substance.get("formatted_duration")
    if ts_formatted_duration:
        ts_add_formatted_duration(ts_roas, ts_formatted_duration, "Duration")

    ts_formatted_aftereffects = ts_substance.get("formatted_aftereffects")
    if ts_formatted_aftereffects:
        ts_add_formatted_duration(ts_roas, ts_formatted_aftereffects, "After effects")

    # merge PW and TS ROAs
    # prioritize PW for ROAs but use TS to fill in gaps

    roas.extend(pw_roas)
    for ts_roa in ts_roas:
        existing_roa = next(
            (roa for roa in roas if roa_matches_name(roa, ts_roa["name"])), None
        )
        # if ROA does not exist, add
        if not existing_roa:
            existing_roa = ts_roa
            roas.append(existing_roa)
            # we want bioavailability from below, so don't skip

        # if ROA does not already have bioavailability, try to get from TS
        if not existing_roa.get("bioavailability"):
            name_lower = ts_roa["name"].lower()
            name_aliases = roa_name_aliases.get(name_lower, [])

            alias_found = next(
                (name_alias in ts_bioavailability for name_alias in name_aliases), None
            )
            # TS has bioavailability if name or any name alias is found
            if name_lower in ts_bioavailability or alias_found:
                existing_roa["bioavailability"] = ts_bioavailability.get(
                    name_lower
                ) or ts_bioavailability.get(alias_found)

        # if existing ROA is missing dosage and TS has dosage, add
        if (not existing_roa.get("dosage") or not len(existing_roa["dosage"])) and (
            "dosage" in ts_roa and ts_roa["dosage"] and len(ts_roa["dosage"])
        ):
            existing_roa["dosage"] = ts_roa["dosage"]

        # if existing ROA is missing duration and TS has duration, add
        if (not existing_roa.get("duration") or not len(existing_roa["duration"])) and (
            "duration" in ts_roa and ts_roa["duration"] and len(ts_roa["duration"])
        ):
            existing_roa["duration"] = ts_roa["duration"]

    interactions = None
    combos = ts_substance.get("combos")
    if combos:
        interactions = []
        for key, combo_data in combos.items():
            if key in ts_combo_ignore:
                continue

            combo_data["name"] = ts_combo_transformations[key]
            interactions.append(combo_data)
        interactions = sorted(interactions, key=lambda i: i["name"])

    if classes != None:
        chemical_class = classes["chemical"]
        psychoactive_class = classes["psychoactive"]
    else:
        chemical_class = None
        psychoactive_class = None

    substance_data.append(
        {
            "id": x,
            "name": name,
            "aliases": list(aliases),
            "aliasesStr": ",".join(aliases),
            "url": url,
            "experiencesUrl": experiences_url,
            "summary": summary,
            "reagents": test_kits,
            "classes": classes,
            "chemicalClass": chemical_class,
            "psychoactiveClass": psychoactive_class,
            "toxicity": toxicity,
            "addictionPotential": addiction_potential,
            "tolerance": tolerance,
            "crossTolerances": cross_tolerances,
            "roas": roas,
            "interactions": interactions,
        }
    )
    x += 1

# output

substances_json = {}
substances_json["substances"] = substance_data
with open(f"ts_pn_data/substances_data.json", "w", encoding="utf-8") as f:
    json.dump(substances_json, fp=f, ensure_ascii=False, indent=2)


substance_aliases = {}

with open("data/lookups/substances.yml", "w", encoding="utf-8") as fp:
    # Lookup Table
    fp.write("""version: "2.0"\nnlu:\n- lookup: substance\n  examples: |\n""")
    for drug in substances_json["substances"]:
        name = re.sub(r"\(.*\)", "", drug["name"])
        fp.write(f"    - {name}\n")
        # Add aliases to lookup table too
        for y in drug["aliases"]:
            y = re.sub(r"\(.*\)", "", y)
            # Check for "or" in aliases and remove
            if " or " in y:
                aliases = y.split(" or ")
                fp.write(f"    - {aliases[0]}\n")
                fp.write(f"    - {aliases[1]}\n")
            elif "or " in y:
                aliases = y.split("or ")
                fp.write(f"    - {aliases[1]}\n")
            else:
                fp.write(f"    - {y}\n")
    fp.write("\n")
    # Synonyms to map aliases to one entity
    for drug in substances_json["substances"]:
        # Skip adding synonym if there are no aliases
        name = re.sub(r"\(.*\)", "", drug["name"])
        substance_aliases[name] = []
        if drug["aliases"] == []:
            continue
        fp.write(f"- synonym: {name}\n  examples: |\n")
        for y in drug["aliases"]:
            y = re.sub(r"\(.*\)", "", y)
            # Check for "or" in aliases and remove
            if " or " in y:
                aliases = y.split(" or ")
                fp.write(f"    - {aliases[0]}\n")
                fp.write(f"    - {aliases[1]}\n")
                substance_aliases[name].append(aliases[0])
                substance_aliases[name].append(aliases[1])
            elif "or " in y:
                aliases = y.split("or ")
                fp.write(f"    - {aliases[1]}\n")
                substance_aliases[name].append(aliases[1])
            else:
                fp.write(f"    - {y}\n")
                substance_aliases[name].append(y)

with open("ts_pn_data/generated_intents.yml", "w", encoding="utf-8") as fp:
    fp.write(DataGen(substances_json).combo_gen())
