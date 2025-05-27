import requests


def download_academia_pdf(query: str):
    '''
    Downloads a pdf from academia.edu
    Args:
        query: The search query.
    Returns:
        None
    '''
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,ta;q=0.8',
        'priority': 'u=1, i',
        'referer': 'https://www.academia.edu/search?langs=en&q=Hooke&utf8=%E2%9C%93&years=2022,2023',
        'sec-ch-ua': '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    }

    params = {
        'camelize_keys': 'true',
        'canonical': 'true',
        'fake_results': 'null',
        'json': 'true',
        'language': 'en',
        'last_seen': 'null',
        'offset': '0',
        'pub_after_date': '2022',
        'pub_before_date': '2023',
        'query': 'Hooke',
        'search_mode': 'works',
        'size': '10',
        'sort': 'relevance',
        'subdomain_param': 'api',
        'user_language': 'en',
    }
    try:
        response = requests.get('https://www.academia.edu/v0/search/integrated_search', params=params, headers=headers)
        rj = response.json()
        works = rj['works']
        if len(works) == 0:
            print("No results found")
            return
        attachments = works[0]['attachments']
        if len(attachments) == 0:
            print("No attachments found")
            return
        attachment = attachments[0]
        url = attachment['bulkDownloadUrl']
        name = attachment['bulkDownloadFileName']
        with open(name, 'wb') as f:
            f.write(requests.get(url).content)
        print(f"Downloaded {name} from academia.edu")
    except Exception as e:
        print(f"Error occured: {e}")



if __name__ == '__main__':
    download_academia_pdf('hooke')

