import json

def save_json(data, dump=False, filename="syntax.json"):
    data = json.dumps(data, default=str) if dump else data
    file = open(filename, "w", encoding="utf8")
    json.dump(data, file, indent=2)
    file.close()


def open_json(filename="syntax.json"):
    f = open(filename, encoding="utf8")
    file_content = json.load(f)
    f.close()
    return file_content