import requests
from bs4 import BeautifulSoup


class StackOverflowAPI:
    BASE_URL = 'https://api.stackexchange.com/2.3/'

    def __init__(self, site='stackoverflow'):
        self.site = site

    def search(self, query, page=1, pagesize=10):
        """
        Searches Stack Overflow for a query.
        """
        endpoint = f'{self.BASE_URL}search'
        params = {
            'order': 'desc',
            'sort': 'relevance',
            'intitle': query,
            'site': self.site,
            'page': page,
            'pagesize': pagesize,
        }

        response = requests.get(endpoint, params=params)
        return response.json()

    def get_answers(self, question_id):
        """
        Fetches answers for a specific question.
        """
        endpoint = f'{self.BASE_URL}questions/{question_id}/answers'
        params = {
            'order': 'desc',
            'sort': 'votes',
            'site': self.site,
        }

        response = requests.get(endpoint, params=params)
        return response.json()

    def get_top_answer(self, question_id):
        """
        Fetches the top answer by score for a specific question.
        """
        answers = self.get_answers(question_id)
        if not answers.get('items'):
            return None

        # Find the answer with the highest score
        top_answer = max(answers['items'], key=lambda x: x['score'])
        return top_answer

    def get_answer_text(self, answer_id):
        """
        Fetches the text content of a Stack Overflow answer by its ID.
        """
        # Stack Exchange API endpoint for answers
        api_url = f'{self.BASE_URL}answers/{answer_id}'
        params = {
            'order': 'desc',
            'sort': 'activity',
            'site': 'stackoverflow',
            'filter': 'withbody',  # Ensures the body is included in the response
        }

        response = requests.get(api_url, params=params)
        data = response.json()

        if 'items' in data and data['items']:
            # Extract the body of the answer
            answer_body_html = data['items'][0]['body']
            # Parse the HTML content to extract text
            soup = BeautifulSoup(answer_body_html, 'html.parser')
            answer_text = soup.get_text()
            return answer_text.strip()
        else:
            return 'Answer not found.'


# Example usage
api = StackOverflowAPI()


def search_in_stack_overflow(query):
    """
    Search Stack Overflow for a query and return the most relevant answer.

    Args:
        query (str): The query to search for.

    Returns:
        str: The most relevant answer to the query.
    """
    # Search for the query
    search_results = api.search(query)

    if search_results.get('items'):
        # Get the most relevant question ID
        top_question = search_results['items'][0]
        question_id = top_question['question_id']

        # Get the top answer for this question
        top_answer = api.get_top_answer(question_id)

        if top_answer:
            question_title = top_question['title']
            answer_text = api.get_answer_text(top_answer['answer_id'])
            return f'Question:\n{question_title}\n\nAnswer:\n{answer_text}'
        else:
            print('No answers found for the top matching question.')
    else:
        print('No questions found matching the query.')


if __name__ == '__main__':
    query = "ImportError: cannot import name 'VectorStoreIndex' from 'llama_index' (unknown location)"
    print(search_in_stack_overflow(query))
