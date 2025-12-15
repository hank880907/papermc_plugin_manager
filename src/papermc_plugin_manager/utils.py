import os
import json

def get_papermc_version():
    version_history_path = "./version_history.json"
    if not os.path.exists(version_history_path):
        return None
    with open(version_history_path, "r") as f:
        version_history = json.load(f)
    if not version_history:
        return None
    return version_history["currentVersion"].split("-")[0]