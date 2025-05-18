import requests
import re
import json
import zipfile
import io
import os
from typing import List, Dict, Any, Callable

TEMP_EXTRACT_DIR_BASE = "temp_repo_extract"

def fetch_source_code_from_zip(zip_url: str, target_path_in_zip: str, downloaded_zip_name: str, script_name: str) -> str | None:
    """
    指定されたURLからZIPファイルをダウンロードし、一時ディレクトリに解凍して特定のファイルのソースコードを取得します。
    """
    # スクリプトごとに一時ディレクトリを分ける
    extract_to_path = os.path.join(os.getcwd(), f"{TEMP_EXTRACT_DIR_BASE}_{script_name}")
    downloaded_zip_path = os.path.join(extract_to_path, downloaded_zip_name)

    try:
        print(f"[{script_name}] Creating temporary directory: {extract_to_path}")
        os.makedirs(extract_to_path, exist_ok=True)

        print(f"[{script_name}] Fetching ZIP archive from: {zip_url}")
        response = requests.get(zip_url, stream=True)
        response.raise_for_status()
        
        print(f"[{script_name}] Saving ZIP archive to: {downloaded_zip_path}")
        with open(downloaded_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[{script_name}] Successfully saved ZIP archive.")

        print(f"[{script_name}] Extracting ZIP archive to: {extract_to_path}")
        with zipfile.ZipFile(downloaded_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to_path)
            print(f"[{script_name}] Successfully extracted ZIP archive.")

            zip_root_dir_name = ""
            if zip_ref.namelist():
                first_entry = zip_ref.namelist()[0]
                if '/' in first_entry:
                    zip_root_dir_name = first_entry.split('/')[0]
                elif '\\' in first_entry: # Handle windows paths in zip
                    zip_root_dir_name = first_entry.split('\\')[0]

            if not zip_root_dir_name:
                print(f"[{script_name}] Error: Could not determine the root directory within the ZIP archive.")
                print(f"[{script_name}] Top level contents of ZIP:")
                for name_in_zip in list(set([item.split('/')[0].split('\\')[0] for item in zip_ref.namelist()[:20]])):
                     print(f" - {name_in_zip}")
                return None

            print(f"[{script_name}] Determined ZIP root directory: {zip_root_dir_name}")
            
            full_target_path = os.path.join(extract_to_path, zip_root_dir_name, target_path_in_zip.replace('/', os.sep))
            
            print(f"[{script_name}] Attempting to read target file: {full_target_path}")
            if os.path.exists(full_target_path):
                with open(full_target_path, 'r', encoding='utf-8') as f_src:
                    source_code = f_src.read()
                print(f"[{script_name}] Successfully read target file: {target_path_in_zip}")
                return source_code
            else:
                print(f"[{script_name}] Error: Target file '{full_target_path}' not found after extraction.")
                print(f"[{script_name}] Please check the path and contents of '{os.path.join(extract_to_path, zip_root_dir_name)}'")
                return None

    except requests.exceptions.RequestException as e:
        print(f"[{script_name}] Error fetching ZIP from {zip_url}: {e}")
        return None
    except zipfile.BadZipFile:
        print(f"[{script_name}] Error: Downloaded file from {zip_url} is not a valid ZIP archive or is corrupted.")
        return None
    except IOError as e:
        print(f"[{script_name}] IOError during file operations: {e}")
        return None
    except Exception as e:
        print(f"[{script_name}] An unexpected error occurred: {e}")
        return None

def create_json_structure(tool_names: List[str], source_url: str) -> Dict[str, Any]:
    """
    抽出されたツール名リストからJSON構造を作成します。
    説明とパラメータはプレースホルダーとして追加します。
    """
    tools_data = []
    for name in tool_names:
        tools_data.append({
            "name": name,
            "description": f"Description for {name} - to be filled manually or by a more advanced parser.",
            "parameters": {}
        })

    return {
        "source_file_url": source_url,
        "comment": "This list was automatically generated. Descriptions and parameters are placeholders.",
        "tools": tools_data
    }

def save_to_json_file(data: Dict[str, Any], filename: str, script_name: str):
    """
    指定されたデータ構造をJSONファイルとして保存します。
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[{script_name}] Successfully saved tool list to: {filename}")
    except IOError as e:
        print(f"[{script_name}] Error saving data to {filename}: {e}")

def process_tools(
    script_name: str,
    github_zip_url: str,
    file_path_in_repo: str,
    downloaded_zip_name: str,
    output_json_file: str,
    extract_tool_names_func: Callable[[str], List[str]]
):
    """
    指定された情報に基づいてツールリストを生成し、JSONファイルに保存するメイン処理。
    """
    print(f"[{script_name}] Starting script to extract available tools...")

    typescript_code = fetch_source_code_from_zip(github_zip_url, file_path_in_repo, downloaded_zip_name, script_name)

    if typescript_code:
        extracted_names = extract_tool_names_func(typescript_code)

        if extracted_names:
            tools_json_data = create_json_structure(extracted_names, github_zip_url)
            save_to_json_file(tools_json_data, output_json_file, script_name)
        else:
            print(f"[{script_name}] No tool names could be extracted. JSON file not created.")
    else:
        print(f"[{script_name}] Failed to fetch source code. Cannot proceed.")

    print(f"[{script_name}] Script finished.")