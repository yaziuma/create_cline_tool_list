import re
from typing import List, Set
from common_utils import process_tools

# 1. GitHubからソースファイルを取得するための情報
GITHUB_ZIP_URL = "https://github.com/RooVetGit/Roo-Code/archive/refs/heads/main.zip"
FILE_PATH_IN_REPO = "src/shared/tools.ts"
DOWNLOADED_ZIP_NAME = "downloaded_repo_roo.zip"

# 出力ファイル名
OUTPUT_JSON_FILE = "roo_available_tools.json"
SCRIPT_NAME = "RooCodeTools"


def extract_tool_names_from_typescript_roo(source_code: str) -> List[str]:
    """
    TypeScriptのソースコードからRoo-Code特有のツール名を抽出します。
    """
    tool_names: Set[str] = set()

    # パターン1: TOOL_DISPLAY_NAMES オブジェクトのキー
    regex_tool_display_names_block = r'TOOL_DISPLAY_NAMES\s*:\s*Record<ToolName,\s*string>\s*=\s*{([^}]+)}'
    display_names_block_match = re.search(regex_tool_display_names_block, source_code, re.DOTALL)
    if display_names_block_match:
        display_names_content = display_names_block_match.group(1)
        regex_keys = r'^\s*([a-zA-Z0-9_]+)\s*:' #行頭からキーを抽出
        found_in_display_names = re.findall(regex_keys, display_names_content, re.MULTILINE)
        for name in found_in_display_names:
            tool_names.add(name)

    # パターン2: TOOL_GROUPS オブジェクト内の tools 配列の要素
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
    regex_switch_case = r'case\s+["\']([^"\']+)["\']\s*:'
    found_in_switch = re.findall(regex_switch_case, source_code)
    for name in found_in_switch:
        tool_names.add(name)

    sorted_tool_names = sorted(list(tool_names))
    print(f"[{SCRIPT_NAME}] Extracted tool names: {sorted_tool_names}")
    return sorted_tool_names

def main():
    process_tools(
        script_name=SCRIPT_NAME,
        github_zip_url=GITHUB_ZIP_URL,
        file_path_in_repo=FILE_PATH_IN_REPO,
        downloaded_zip_name=DOWNLOADED_ZIP_NAME,
        output_json_file=OUTPUT_JSON_FILE,
        extract_tool_names_func=extract_tool_names_from_typescript_roo
    )

if __name__ == "__main__":
    main()