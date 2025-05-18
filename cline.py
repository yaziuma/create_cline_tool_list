import re
from typing import List, Set
from common_utils import process_tools

# 1. GitHubからソースファイルを取得するための情報
GITHUB_ZIP_URL = "https://github.com/cline/cline/archive/refs/heads/main.zip"
FILE_PATH_IN_REPO = "src/core/task/index.ts"
DOWNLOADED_ZIP_NAME = "downloaded_repo_cline.zip" # cline用に変更

# 出力ファイル名
OUTPUT_JSON_FILE = "cline_available_tools.json"
SCRIPT_NAME = "ClineTools"


def extract_tool_names_from_typescript_cline(source_code: str) -> List[str]:
    """
    TypeScriptのソースコードからCline特有のツール名を抽出します。
    """
    tool_names: Set[str] = set()

    # パターン1: switch文の case "tool_name":
    regex_switch_case = r'case\s+["\']([^"\']+)["\']\s*:'
    found_in_switch = re.findall(regex_switch_case, source_code)
    for name in found_in_switch:
        if '_' in name or name.endswith('File') or name.endswith('Files') or 'command' in name.lower() or 'mcp' in name.lower() or 'action' in name.lower():
             tool_names.add(name)
        elif name in ["thinking", "attempt_completion", "plan_mode_response", "ask_followup_question"]:
             tool_names.add(name)

    # パターン2: ツール名を要素とする配列の定義
    regex_tool_array = r'(?:tools|commands)\s*:\s*\[([^\]]+)\]'
    array_matches = re.findall(regex_tool_array, source_code)
    for match in array_matches:
        array_elements = re.findall(r'["\']([^"\']+)["\']', match)
        for el in array_elements:
            tool_names.add(el)
            
    # パターン3: 'registerTool('tool_name', ...)' のような関数呼び出し
    regex_register_tool = r'registerTool\s*\(\s*["\']([^"\']+)["\']'
    found_in_register = re.findall(regex_register_tool, source_code)
    for name in found_in_register:
        tool_names.add(name)

    sorted_tool_names = sorted(list(tool_names))
    print(f"[{SCRIPT_NAME}] Extracted tool names: {sorted_tool_names}")
    return sorted_tool_names

if __name__ == "__main__":
    process_tools(
        script_name=SCRIPT_NAME,
        github_zip_url=GITHUB_ZIP_URL,
        file_path_in_repo=FILE_PATH_IN_REPO,
        downloaded_zip_name=DOWNLOADED_ZIP_NAME,
        output_json_file=OUTPUT_JSON_FILE,
        extract_tool_names_func=extract_tool_names_from_typescript_cline
    )