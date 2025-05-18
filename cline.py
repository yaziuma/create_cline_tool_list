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
FILE_PATH_IN_REPO = "src/core/task/index.ts" # Path within the zip structure (after the root folder)
# ZIP_ROOT_DIR_PATTERN = r"cline-main/" # Pattern to identify the root directory in the zip. Will be determined dynamically.

# URL for the zip file
GITHUB_ZIP_URL = "https://github.com/cline/cline/archive/refs/heads/main.zip"
TEMP_EXTRACT_DIR = "temp_cline_repo_extract" # Directory to extract files
DOWNLOADED_ZIP_NAME = "downloaded_repo.zip"

# 出力ファイル名
OUTPUT_JSON_FILE = "cline_available_tools.json"

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

    # パターン1: switch文の case "tool_name":
    # 例: case "read_file":
    #     case "write_to_file":
    #     case "replace_in_file":
    #     case "search_files":
    #     case "list_files":
    #     case "list_code_definition_names":
    #     case "execute_command":
    #     case "browser_action":
    #     case "use_mcp_tool":
    #     case "access_mcp_resource":
    #     case "ask_followup_question":
    #     case "attempt_completion":
    #     case "plan_mode_response":
    #     case "thinking":

    # case "toolName": or case 'toolName':
    regex_switch_case = r'case\s+["\']([^"\']+)["\']\s*:'
    found_in_switch = re.findall(regex_switch_case, source_code)
    for name in found_in_switch:
        # "image_url" のような一般的なケースを除外するためのヒューリスティック
        # ここでは、既知のツール名パターンや、アンダースコアを含む、
        # または特定のキーワードで始まるものを優先的にツールとみなすなどが考えられます。
        # 今回は抽出されたものをそのまま採用し、後で手動でフィルタリングすることも可能です。
        if '_' in name or name.endswith('File') or name.endswith('Files') or 'command' in name.lower() or 'mcp' in name.lower() or 'action' in name.lower():
             tool_names.add(name)
        elif name in ["thinking", "attempt_completion", "plan_mode_response", "ask_followup_question"]: # 既知のツールを明示的に追加
             tool_names.add(name)


    # パターン2: ツール名を要素とする配列の定義 (例: const availableTools = ["tool1", "tool2"];)
    # const tools: string[] = ["tool1", "tool2"];
    # tools: ["tool1", "tool2"]
    # このパターンは Cline.ts の現在の構造では主要ではないかもしれませんが、将来の変更や他のファイルで使われる可能性を考慮
    regex_tool_array = r'(?:tools|commands)\s*:\s*\[([^\]]+)\]'
    array_matches = re.findall(regex_tool_array, source_code)
    for match in array_matches:
        # 配列内の文字列リテラルを抽出
        array_elements = re.findall(r'["\']([^"\']+)["\']', match)
        for el in array_elements:
            tool_names.add(el)
            
    # パターン3: 'registerTool('tool_name', ...)' のような関数呼び出し
    # (これは一般的なパターンであり、実際のコード構造に依存します)
    regex_register_tool = r'registerTool\s*\(\s*["\']([^"\']+)["\']'
    found_in_register = re.findall(regex_register_tool, source_code)
    for name in found_in_register:
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