import requests

from openhands.runtime.plugins.agent_skills.file_ops.academic_utils.utils import (
    download_pdf_from_url,
)

headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Origin': 'https://oa.mg',
    'Referer': 'https://oa.mg/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


def download_oa_papers(query: str):
    """
    Download OA papers from OpenAlex
    Args:
        query: str, the query to search for
    """
    url = f'https://api.openalex.org/works?search={query}&per-page=99&page=1&sort=relevance_score:desc'
    response = requests.get(url, headers=headers)

    rj = response.json()

    for result in rj['results']:
        is_oa = result['open_access']['is_oa']
        if is_oa:
            link = result['open_access']['oa_url']
            if 'arxiv' in link:
                print(f'Downloading from {link}')
                download_pdf_from_url(link)
            else:
                print(f'Download from {link}')
            break
