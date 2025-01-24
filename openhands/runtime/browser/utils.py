import os

from browsergym.utils.obs import flatten_axtree_to_str

from openhands.core.exceptions import BrowserUnavailableException
from openhands.core.logger import openhands_logger as logger
from openhands.core.schema import ActionType
from openhands.events.action import BrowseInteractiveAction, BrowseURLAction
from openhands.events.observation import BrowserOutputObservation
from openhands.runtime.browser.browser_env import BrowserEnv
from openhands.utils.async_utils import call_sync_from_async


async def browse(
    action: BrowseURLAction | BrowseInteractiveAction, browser: BrowserEnv | None
) -> BrowserOutputObservation:
    if browser is None:
        raise BrowserUnavailableException()

    if isinstance(action, BrowseURLAction):
        # legacy BrowseURLAction
        asked_url = action.url.strip()
        if not asked_url.startswith('http'):
            asked_url = os.path.abspath(os.curdir) + action.url
        action_str = f'goto("{asked_url}")'

    elif isinstance(action, BrowseInteractiveAction):
        # new BrowseInteractiveAction, supports full featured BrowserGym actions
        # action in BrowserGym: see https://github.com/ServiceNow/BrowserGym/blob/main/core/src/browsergym/core/action/functions.py
        action_str = action.browser_actions
    else:
        raise ValueError(f'Invalid action type: {action.action}')

    try:
        if 'summarize' in action_str:
            raise ValueError('Summarize is an invalid action')
        if action_str.startswith('curl'):
            raise ValueError('curl is an bash action')
        # obs provided by BrowserGym:
        # https://github.com/ServiceNow/BrowserGym/blob/main/browsergym/core/src/browsergym/core/env.py#L521
        # https://github.com/ServiceNow/BrowserGym/blob/418421abdc5da4d77dc71d3b82a9e5e931be0c4f/browsergym/core/src/browsergym/core/env.py#L521
        obs = await call_sync_from_async(browser.step, action_str)
        try:
            axtree_txt = flatten_axtree_to_str(
                obs['axtree_object'],  # accessibility tree object
                extra_properties=obs[
                    'extra_element_properties'
                ],  # extra element properties
                with_clickable=True,
                filter_visible_only=True,
            )
        except Exception as e:
            logger.error(
                f'Error when trying to process the accessibility tree: {e}, obs: {obs}'
            )
            axtree_txt = f'AX Error: {e}'
        return BrowserOutputObservation(
            content=obs['text_content'],  # text content of the page
            url=obs.get('url', ''),  # URL of the page
            screenshot=obs.get('screenshot', ''),  # base64-encoded screenshot, png
            set_of_marks=obs.get(
                'set_of_marks', ''
            ),  # base64-encoded Set-of-Marks annotated screenshot, png,
            goal_image_urls=obs.get('image_content', []),
            open_pages_urls=obs.get('open_pages_urls', []),  # list of open pages
            active_page_index=obs.get(
                'active_page_index', -1
            ),  # index of the active page
            axtree_txt=axtree_txt,  # accessibility tree text
            focused_element_bid=obs.get(
                'focused_element_bid', ''
            ),  # focused element bid
            last_browser_action=obs.get(
                'last_action', ''
            ),  # last browser env action performed
            last_browser_action_error=obs.get('last_action_error', ''),
            error=True if obs.get('last_action_error') else False,  # error flag
            trigger_by_action=action.action,
        )
    except Exception as e:
        return BrowserOutputObservation(
            content=str(e),
            screenshot='',
            error=True,
            last_browser_action_error=str(e),
            url=asked_url if action.action == ActionType.BROWSE else '',
            trigger_by_action=action.action,
        )
