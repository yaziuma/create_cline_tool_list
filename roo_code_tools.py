import requests
import re
import json
import zipfile
import io
import os
from typing import List, Dict, Any, Set

# 1. GitHubからソースファイルを取得するための情報
# cline/cline リポジトリの src/core/Cline.ts ファイルを対象とします
# GITHUB_REPO_OWNER = "cline" # No longer needed directly for zip URL
# GITHUB_REPO_NAME = "cline" # No longer needed directly for zip URL
# GITHUB_BRANCH_OR_TAG = "main" # Part of the zip URL
FILE_PATH_IN_REPO = "src/shared/tools.ts" # Path within the zip structure (after the root folder)
# ZIP_ROOT_DIR_PATTERN = r"cline-main/" # Pattern to identify the root directory in the zip. Will be determined dynamically.

# URL for the zip file
GITHUB_ZIP_URL = "https://github.com/RooVetGit/Roo-Code/archive/refs/heads/main.zip"
TEMP_EXTRACT_DIR = "temp_cline_repo_extract" # Directory to extract files
DOWNLOADED_ZIP_NAME = "downloaded_repo_roo.zip"

# 出力ファイル名
OUTPUT_JSON_FILE = "roo_available_tools.json"

def fetch_source_code_from_zip(zip_url: str, target_path_in_zip: str) -> str | None:
    """
    指定されたURLからZIPファイルをダウンロードし、一時ディレクトリに解凍して特定のファイルのソースコードを取得します。
    """
    extract_to_path = os.path.join(os.getcwd(), TEMP_EXTRACT_DIR)
    downloaded_zip_path = os.path.join(extract_to_path, DOWNLOADED_ZIP_NAME)

    try:
        print(f"Creating temporary directory: {extract_to_path}")
        os.makedirs(extract_to_path, exist_ok=True)

        print(f"Fetching ZIP archive from: {zip_url}")
        response = requests.get(zip_url, stream=True)
        response.raise_for_status()
        
        print(f"Saving ZIP archive to: {downloaded_zip_path}")
        with open(downloaded_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Successfully saved ZIP archive.")

        print(f"Extracting ZIP archive to: {extract_to_path}")
        with zipfile.ZipFile(downloaded_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to_path)
            print("Successfully extracted ZIP archive.")

            # Determine the root directory name within the zip (e.g., "cline-main")
            # This is typically the first entry in the zip file list if it's a directory.
            zip_root_dir_name = ""
            if zip_ref.namelist():
                first_entry = zip_ref.namelist()[0]
                if '/' in first_entry:
                    zip_root_dir_name = first_entry.split('/')[0]
                elif '\\' in first_entry: # Handle windows paths in zip
                    zip_root_dir_name = first_entry.split('\\')[0]

            if not zip_root_dir_name:
                print("Error: Could not determine the root directory within the ZIP archive.")
                # Attempt to list files to help debug
                print("Top level contents of ZIP:")
                for name_in_zip in list(set([item.split('/')[0].split('\\')[0] for item in zip_ref.namelist()[:20]])):
                     print(f" - {name_in_zip}")
                return None

            print(f"Determined ZIP root directory: {zip_root_dir_name}")
            
            # Construct the full path to the target file after extraction
            # os.path.join will handle OS-specific separators
            full_target_path = os.path.join(extract_to_path, zip_root_dir_name, target_path_in_zip.replace('/', os.sep))
            
            print(f"Attempting to read target file: {full_target_path}")
            if os.path.exists(full_target_path):
                with open(full_target_path, 'r', encoding='utf-8') as f_src:
                    source_code = f_src.read()
                print(f"Successfully read target file: {target_path_in_zip}")
                return source_code
            else:
                print(f"Error: Target file '{full_target_path}' not found after extraction.")
                print(f"Please check the path and contents of '{os.path.join(extract_to_path, zip_root_dir_name)}'")
                return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching ZIP from {zip_url}: {e}")
        return None
    except zipfile.BadZipFile:
        print(f"Error: Downloaded file from {zip_url} is not a valid ZIP archive or is corrupted.")
        return None
    except IOError as e:
        print(f"IOError during file operations: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    # finally:
        # Optional: Clean up the temporary directory and downloaded zip file
        # print(f"Cleaning up temporary directory: {extract_to_path}")
        # import shutil
        # if os.path.exists(extract_to_path):
        #     shutil.rmtree(extract_to_path)
        # print("Cleanup complete.")

def extract_tool_names_from_typescript(source_code: str) -> List[str]:
    """
    TypeScriptのソースコードからツール名を抽出します。
    主に 'case "tool_name":' のようなパターンや、
    ツールが文字列リテラルとして定義されていそうな箇所を探します。
    """
    tool_names: Set[str] = set()

    # パターン1: TOOL_DISPLAY_NAMES オブジェクトのキー
    # export const TOOL_DISPLAY_NAMES: Record<ToolName, string> = { execute_command: "run commands", ... }
    regex_tool_display_names_block = r'TOOL_DISPLAY_NAMES\s*:\s*Record<ToolName,\s*string>\s*=\s*{([^}]+)}'
    display_names_block_match = re.search(regex_tool_display_names_block, source_code, re.DOTALL)
    if display_names_block_match:
        display_names_content = display_names_block_match.group(1)
        # キーを抽出: `key:` または `key :`
        regex_keys = r'^\s*([a-zA-Z0-9_]+)\s*:' #行頭からキーを抽出
        found_in_display_names = re.findall(regex_keys, display_names_content, re.MULTILINE)
        for name in found_in_display_names:
            tool_names.add(name)

    # パターン2: TOOL_GROUPS オブジェクト内の tools 配列の要素
    # export const TOOL_GROUPS: Record<ToolGroup, ToolGroupConfig> = { read: { tools: ["read_file", ...], }, ... }
    regex_tool_groups_block = r'TOOL_GROUPS\s*:\s*Record<ToolGroup,\s*ToolGroupConfig>\s*=\s*{([^}]+)}'
    tool_groups_block_match = re.search(regex_tool_groups_block, source_code, re.DOTALL)
    if tool_groups_block_match:
        tool_groups_content = tool_groups_block_match.group(1)
        regex_tools_array = r'tools\s*:\s*\[([^\]]+)\]'
        tools_array_matches = re.findall(regex_tools_array, tool_groups_content)
        for match in tools_array_matches:
            array_elements = re.findall(r'["\']([^"\']+)["\']', match)
            for el in array_elements:
                tool_names.add(el)

    # パターン3: ALWAYS_AVAILABLE_TOOLS 配列の要素
    # export const ALWAYS_AVAILABLE_TOOLS: ToolName[] = [ "ask_followup_question", ... ]
    regex_always_available_block = r'ALWAYS_AVAILABLE_TOOLS\s*:\s*ToolName\[\]\s*=\s*\[([^\]]+)\]'
    always_available_match = re.search(regex_always_available_block, source_code)
    if always_available_match:
        always_available_content = always_available_match.group(1)
        array_elements = re.findall(r'["\']([^"\']+)["\']', always_available_content)
        for el in array_elements:
            tool_names.add(el)

    # パターン4: `interface XXXToolUse extends ToolUse { name: "tool_name" ... }`
    regex_interface_tool_name = r'interface\s+\w+ToolUse\s+extends\s+ToolUse\s*{\s*name\s*:\s*["\']([^"\']+)["\']'
    found_in_interfaces = re.findall(regex_interface_tool_name, source_code)
    for name in found_in_interfaces:
        tool_names.add(name)
        
    # パターン5: (cline.pyから流用) switch文の case "tool_name":
    # Roo-Codeのtools.tsには直接この形式はないかもしれないが、他のファイルで使われる可能性を考慮
    regex_switch_case = r'case\s+["\']([^"\']+)["\']\s*:'
    found_in_switch = re.findall(regex_switch_case, source_code)
    for name in found_in_switch:
        tool_names.add(name)


    # 抽出されたツール名リストをソートして返す
    sorted_tool_names = sorted(list(tool_names))
    print(f"Extracted tool names: {sorted_tool_names}")
    return sorted_tool_names

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
            "parameters": {} # パラメータ構造も手動または詳細な解析で定義
        })

    return {
        "source_file_url": source_url,
        "comment": "This list was automatically generated. Descriptions and parameters are placeholders.",
        "tools": tools_data
    }

def save_to_json_file(data: Dict[str, Any], filename: str):
    """
    指定されたデータ構造をJSONファイルとして保存します。
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved tool list to: {filename}")
    except IOError as e:
        print(f"Error saving data to {filename}: {e}")

if __name__ == "__main__":
    print("Starting script to extract available tools...")

    # 1. GitHubからZIPアーカイブを取得し、目的のファイルを展開
    typescript_code = fetch_source_code_from_zip(GITHUB_ZIP_URL, FILE_PATH_IN_REPO)

    if typescript_code:
        # 2. ソースコードからツール名を抽出
        extracted_names = extract_tool_names_from_typescript(typescript_code)

        if extracted_names:
            # 3. JSON構造を作成
            # ソースURLはZIPファイルのURLを記録する
            tools_json_data = create_json_structure(extracted_names, GITHUB_ZIP_URL)

            # 4. JSONファイルとして保存
            save_to_json_file(tools_json_data, OUTPUT_JSON_FILE)
        else:
            print("No tool names could be extracted. JSON file not created.")
    else:
        print("Failed to fetch source code. Cannot proceed.")

    print("Script finished.")