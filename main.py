import os
import config as cfg
import multiprocessing
import json
import requests
import datetime
from datetime import date, datetime, timedelta

json_directory = cfg.jsonPath
webhook_directory = cfg.webHookPath
console_prints = True
with open(
    f"{webhook_directory}/webhooks.json",
    "r",
) as f:
    webhook = json.load(f)

threads_array = []

bot_name = "LaDose"


def check_availabilities(dc_item):
    headers = {
        "authority": "www.doctolib.fr",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
        "accept": "application/json",
        "sec-ch-ua-mobile": "?0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "content-type": "application/json; charset=utf-8",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://www.doctolib.fr/centre-de-sante/",
        "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    params = (
        ("start_date", date.today().strftime("%Y-%m-%d")),
        ("visit_motive_ids", dc_item["visit_motive_ids"]),
        ("agenda_ids", dc_item["agenda_ids"]),
        ("insurance_sector", "public"),
        ("practice_ids", dc_item["practice_ids"]),
        ("destroy_temporary", "true"),
        ("limit", "4"),
    )

    response = requests.get(
        "https://www.doctolib.fr/availabilities.json", headers=headers, params=params
    )
    slots = response.json()
    return slots


def send_alert(content, e_title, e_desc, e_url, webhook_url):
    data = {"content": content, "username": bot_name}
    data["embeds"] = [{"description": e_desc, "title": e_title, "url": e_url}]
    result = requests.post(webhook_url, json=data)
    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if console_prints:
            print(err)
    else:
        if console_prints:
            print("Payload delivered successfully, code {}.".format(result.status_code))


def handleProcess(jsonFile):
    with open(
        jsonFile,
        "r",
    ) as f:
        doctolib_lookup = json.load(f)
        end_date = date.today() + timedelta(days=2)
        dep_number = jsonFile.split("splitted/")[1].split("_")[0]
        webhook_url = webhook.get(f"{dep_number}")
        for dc_item in doctolib_lookup:
            slots = check_availabilities(dc_item)
            if slots["total"] > 0:
                if console_prints:
                    print("Slots available")
                for dates in slots["availabilities"]:
                    if len(dates["slots"]) > 0:
                        slot_times = [
                            str(
                                datetime.strptime(
                                    stime["start_date"].split("+")[0],
                                    "%Y-%m-%dT%H:%M:%S.%f",
                                ).time()
                            )
                            for stime in dates["slots"]
                        ]
                        if (
                            end_date
                            > datetime.strptime(dates["date"], "%Y-%m-%d").date()
                        ):
                            send_alert(
                                content="Dose de vaccin disponible",
                                e_title=str(dates["date"]),
                                e_desc="\n".join(slot_times),
                                e_url=dc_item["url"],
                                webhook_url=webhook_url,
                            )
            else:
                if console_prints:
                    print("No slots")


for filename in os.listdir(json_directory):
    if filename.endswith(".json") and webhook:
        process = multiprocessing.Process(
            target=handleProcess, args=(os.path.join(json_directory, filename),)
        )
        threads_array.append(process)
        process.start()


for thread in threads_array:
    thread.join()

print("finished")
