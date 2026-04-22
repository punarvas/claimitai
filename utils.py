from paddleocr import PaddleOCRVL
import os
import json
from pathlib import Path
import re
from collections import defaultdict
from openai import OpenAI

client = OpenAI()

def process_document(filenames, save_dir):
    pipeline = PaddleOCRVL()
    saved_paths = []
    for i, filename in enumerate(filenames):
        save_path = os.path.join(save_dir, f"file_{i:02}.json")
        if filename.suffix == ".txt":
            with open(filename, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            data = {
                "input_path": str(filename),
                "contents": lines
            }
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        else:
            output = pipeline.predict(str(filename))
            for res in output:
                res.save_to_json(save_path=save_path)
        saved_paths.append(save_path)
    return saved_paths

def html_to_text(html_str):
    text = re.sub(r"<[^>]+>", " ", html_str)
    return " ".join(text.split())

def process_parsing_res_list(data):
    """Group block_content entries by block_label (with table parsing) and include input_path."""
    grouped = defaultdict(list)

    for item in data["parsing_res_list"]:
        block_label = item.get("block_label")
        block_content = item.get("block_content")

        if block_label is None:
            continue
        else:
            if block_label == "table":
                block_content = html_to_text(block_content)
            grouped[block_label].append(block_content)

    return {
        "input_path": data["input_path"],
        **dict(grouped)
    }


def process_contents(data):
    """Return contents under text and include input_path."""
    return {
        "input_path": data["input_path"],
        "text": data.get("contents", [])
    }


def process_file(filepath):
    """Process one JSON file according to available keys."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "parsing_res_list" in data:
        return process_parsing_res_list(data)

    if "contents" in data:
        return process_contents(data)

    return {
        "input_path": data.get("input_path"),
        "text": []
    }

def build_master_information(filenames, save_dir, session_id):
    master = {}
    for filepath in filenames:
        stem = Path(filepath).stem
        master[stem] = process_file(filepath)  # type: ignore

    output_path = os.path.join(save_dir, f"{session_id}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(master, f, indent=4, ensure_ascii=False)

    print(f"Saved master JSON to: {output_path}")
    return output_path


def ai_formatter(filepath):
    with open(filepath, mode="r", encoding="utf-8") as f:
        lines = f.readlines()
        source = "\n".join(lines)

    # System prompt
    filename = "prompts\\specialist.json"
    with open(filename, "r") as f:
        prompt = json.load(f)

    # output format
    with open("prompts\\specialist_format.txt", "r") as f:
        lines = f.readlines()
        target = "\n".join(lines)

    system_content = prompt["system"]
    user_content = prompt["user"]

    # attach the JSON
    user_content = user_content.replace("##SOURCE##", source)
    user_content = user_content.replace("##TARGET##", target)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[  # type: ignore
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ])

    # results = json.loads()
    filepath = Path(filepath)
    save_dir = str(filepath.parent)
    savename = os.path.join(save_dir, f"{filepath.stem}_ai.json")
    with open(savename, "w") as f:
        f.write(str(response.choices[0].message.content))
    return savename