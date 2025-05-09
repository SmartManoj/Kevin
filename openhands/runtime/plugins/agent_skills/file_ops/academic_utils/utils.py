import os
import re

import arxiv
import requests
from fuzzywuzzy import fuzz
from scholarly import scholarly
from semanticscholar import SemanticScholar



def clean_filename(filename: str):
    # remove special characters
    filename = re.sub(r'[^\w\s-]', '', filename)
    # remove leading and trailing whitespace
    filename = filename.strip()
    return filename


def download_arxiv_pdf(query: str):
    """
    Searches arXiv for papers matching the given query and saves the pdf to the current directory.

    Args:
        query: The search query.
        max_results: The maximum number of results to return.

    Returns:
        A list of arXiv results.
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=10,  # Increase initial results for better fuzzy matching
        sort_by=arxiv.SortCriterion.Relevance,  # not working as expected
    )
    results = list(client.results(search))

    # Use fuzzy matching to find relevant results
    relevant_results = []
    for result in results:
        score = fuzz.partial_ratio(query.lower(), result.title.lower())
        if score >= 80:  # Adjust the threshold as needed
            relevant_results.append((result, score))

    # Sort by fuzzy matching score and return top results
    relevant_results.sort(key=lambda x: x[1], reverse=True)
    if len(relevant_results) > 0:
        relevant_result = relevant_results[0][0]
        print(
            relevant_result.download_pdf(
                filename=f'{clean_filename(relevant_result.title)}.pdf'
            )
        )
        print(f'Downloaded to {relevant_result.title}.pdf')
    else:
        print('No relevant results found')


def download_pdf_from_url(url: str, name: str | None = None):
    if name is None:
        name = url.split('/')[-1]
    response = requests.get(url)
    if response.status_code == 200:
        with open(name, 'wb') as f:
            f.write(response.content)
        print('PDF downloaded successfully.')
    else:
        print(f'Failed to download PDF. Status code: {response.status_code}')


def download_semantic_scholar_pdf(query: str | None = None, url: str | None = None):
    """
    Download a paper from semantic scholar using the semantic scholar library
    Args:
        query: The search query.
        url: The url of the paper.
    """
    sch = SemanticScholar()
    if query:
        results = sch.search_paper(query)
        print(f'{results.total} results.', f'First occurrence: {results[0].title}.')

        if results.total == 0:
            print('No results found')
            return
        url = results[0].url
    print('Use Browser Use')


def download_google_scholar_paper(search_query: str):
    """
    Download a paper from google scholar using the scholarly library
    Args:
        search_query: The search query.
    """
    search_results = scholarly.search_pubs(search_query)
    try:
        first_result = next(search_results)
        print(f"Title: {first_result['bib']['title']}")
        print(f"URL: {first_result['pub_url']}")

        if 'eprint' in first_result:
            pdf_url = first_result['eprint']
            print(f'PDF URL: {pdf_url}')
        elif first_result['pub_url']:
            pdf_url = first_result['pub_url'].replace('/abs/', '/pdf/') + '.pdf'
            print(f'Trying PDF URL: {pdf_url}')
            download_pdf_from_url(
                pdf_url, name=f"{clean_filename(first_result['bib']['title'])}.pdf"
            )
        else:
            print('No PDF link found in the search result.')
            exit()

    except StopIteration:
        print('No results found for the given query.')
    except Exception as e:
        print(f'An error occurred: {e}')


def download_papers_using_pypaperbot(
    query: str, scholar_pages: int = 1, max_dwn_year: int = 1
):
    """
    Download a paper using the PyPaperBot library
    Args:
        query: The search query.
        scholar_pages: The number of pages to search on scholar.
        max_dwn_year: The maximum year to download papers from.
    """
    cmd = f'python -m PyPaperBot --query={query}  --dwn-dir=/workspace/papers --scholar-pages={scholar_pages} --max-dwn-year={max_dwn_year}'
    os.system(cmd)
    print(f'Downloaded {query} to /workspace/papers')


if __name__ == '__main__':
    query = (
        'OpenHands: An Open Platform for AI Software Developers as Generalist Agents'
    )
    url = (
        'https://www.semanticscholar.org/paper/1d07e5b6f978cf69c0186f3d5f434fa92d471e46'
    )
    # download_semanticscholar_pdf(url=url)
    url = 'https://arxiv.org/pdf/2407.16741.pdf'
    # download_pdf_from_url(url)
    download_google_scholar_paper(query)
