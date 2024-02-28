import argparse
import base64
import os
import re
from typing import List

import colorama
import requests
from bs4 import BeautifulSoup

filepath = ''  # The css file to convert. Can be a URL.
output_path = 'output.css' # The output filepath.
log_method = 1  # 0 for none, 1 for print, 2 for file, 3 for both print and file
log_level = 1  # 0 for none, 1 for normal, 2 for verbose
user_agent = None  # The user agent to use for requesting assets
minify = True # Whether to minify the css

headers = {'User-Agent': user_agent} if user_agent else None  # This should not be changed


def _log(content: str, prefix: str = None) -> None:
    if log_method in [2, 3]:
        with open('css_extractor_output.log', 'a', encoding='UTF-8') as f:
            f.write(content + '\n')
    if log_method in [1, 3]:
        if prefix is not None:
            content = f'{colorama.Fore.LIGHTMAGENTA_EX}[{prefix.upper()}]{colorama.Style.RESET_ALL}: {colorama.Fore.CYAN}{content}{colorama.Style.RESET_ALL}'
        else:
            content = f'{colorama.Fore.CYAN}{content}{colorama.Style.RESET_ALL}'
        print(f'{colorama.Fore.GREEN}[LOG]{colorama.Style.RESET_ALL}:', content)


def test_minify_css(css: str) -> str:
    """
    Minifies the given css
    """
    css = re.sub(r'/\*[^*]*\*+(?:[^*/][^*]*\*+)*/', '', css)
    css = re.sub(r'\s+', ' ', css)

    css = css.strip()

    return css


def test_import_extractor(css: str) -> List[str]:
    """
    Extracts import URLs from a css file
    """
    imports = re.compile(r'@import\s+(url\()?[\'"]?(.*?)[\'"]?\)?;').findall(css)
    import_urls = []
    for _import in imports:
        import_urls.append(_import[1])

    return import_urls


def test_asset_extractor(css: str) -> List[str]:
    """
    Extracts all asset URLs from a css file
    """
    if log_level in [1, 2]:
        _log('Extracting URLs...')

    assets = re.compile(r'url\([\'"]?(.*?)[\'"]?\)').findall(css)
    return assets


def test_import_resolver(urls: List[str], css: str) -> str:
    """
    Resolves and embeds all imports in a css file
    """
    embedded = css

    for url in urls:
        if log_level == 2:
            _log(f'Embedding content of {url}...', 'verbose')
        try:
            if url.startswith('/') and log_level in [1, 2]:
                _log(f'Skipping broken import url: {url}')
                continue # I might add something to attempt to guess the domain based on the other URLs later, but too much work for right now :3

            if log_level == 2:
                _log(f'Requesting {url}...', 'verbose')

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                if log_level == 2:
                    _log(f'Embedding {url}...', 'verbose')

                content = response.text
                resolved_content = test_resolve_css(content) # Making sure the imported css is fully resolved before adding it to our main file
                embedded = re.sub(fr'@import\s+(?:url\()?[\'"]?{re.escape(url)}[\'"]?\)?;', resolved_content, embedded) # Making sure that different ways of importing don't screw us up here
                _log(f"Failed to download: {url}", str(response.status_code))
        except Exception as e:
            if log_level in [1, 2]:
                _log(f"Error embedding {url}", str(e))

    return embedded


def test_asset_resolver(urls: List[str], css: str) -> str:
    """
    Resolves all assets in the given css
    """
    embedded = css

    for url in urls:
        if 'data:' in url:
            if log_level == 2:
                _log(f'Skipping data url...', 'verbose')
            continue  # Skipping data urls because they're already embedded :3
        try:
            if url.startswith('/') and log_level in [1, 2]:
                _log(f'Skipping broken asset url: {url}')
                continue

            if log_level == 2:
                _log(f'Requesting {url}...', 'verbose')

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                if log_level == 2:
                    _log(f'Embedding {url}...', 'verbose')

                content_type = response.headers.get('content-type')
                data = base64.b64encode(response.content).decode('utf-8') # Encoding the data into base64. For SVGs it would probaby be better just to use the raw content, but we might get other filetypes sometimes and I'm too lazy to make it check
                embedded = embedded.replace(url, f"data:{content_type};base64,{data}")
            elif log_level in [1, 2]:
                _log(f"Failed to download: {url}", str(response.status_code))
        except Exception as e:
            if log_level in [1, 2]:
                _log(f"Error embedding {url}", str(e))

    return embedded


def test_resolve_css(css: str) -> str:
    """
    Fully resolves a css string.
    """
    embedded = css

    imports = test_import_extractor(embedded)
    embedded = test_import_resolver(imports, embedded)

    assets = test_asset_extractor(embedded)
    embedded = test_asset_resolver(assets, embedded)

    return embedded


def test_extract(path: str, compress: bool = True) -> str:
    """
    Fully resolves a css file.
    `path` can either be a filepath or a URL.
    """
    if path.startswith('http') and '://' in path:
        if log_level in [1, 2]:
            _log(f'Downloading css file: {path}')
        css = requests.get(filepath, headers=headers).text
    else:
        if not os.path.exists(filepath):
            _log(f'The path {filepath} does not exist. Skipping...')
            return
        with open(filepath, 'r') as f:
            css = f.read()

    embedded = resolve_css(css)

    if compress:
        if log_level in [1, 2]:
            _log(f'Compressing css...')
        embedded = minify_css(embedded)

    return embedded


__all__ = [
    'test_minify_css',
    'test_import_extractor',
    'test_asset_extractor',
    'test_import_resolver',
    'test_asset_resolver',
    'test_resolve_css',
    'test_extract'
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSS Downloader and Minifier")

    parser.add_argument('filepath', type=str, help='Path to the CSS file or URL')
    parser.add_argument('output-path', type=str, default='output.css', help='Path to write the output to')
    parser.add_argument('--log-method', type=int, choices=[0, 1, 2, 3], default=1, help='Logging method (0: none, 1: print, 2: file, 3: both)')
    parser.add_argument('--log-level', type=int, choices=[0, 1, 2], default=1, help='Logging level (0: none, 1: normal, 2: verbose)')
    parser.add_argument('--user-agent', type=str, default=None, help='User agent for requesting assets')
    parser.add_argument('--minify', type=bool, choices=[True, False], default=True, help='Whether to minify the output css')

    args = parser.parse_args()

    filepath = getattr(args, 'filepath')
    output_path = getattr(args, 'output-path')
    log_method = getattr(args, 'log_method')
    log_level = getattr(args, 'log_level')
    user_agent = getattr(args, 'user_agent')
    compress = getattr(args, 'minify')

    headers = {'User-Agent': user_agent} if user_agent else None

    embedded = extract(filepath, compress)

    with open(output_path, 'w', encoding='UTF-8') as f:
        f.write(embedded)

    _log(f'Output saved to {os.path.abspath(output_path)}', 'finished')
