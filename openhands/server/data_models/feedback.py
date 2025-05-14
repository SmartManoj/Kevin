import json
import os
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from openhands.core.logger import openhands_logger as logger


class FeedbackDataModel(BaseModel):
    version: str
    email: str
    polarity: Literal['positive', 'negative']
    feedback: Literal[
        'positive', 'negative'
    ]  # TODO: remove this, its here for backward compatibility
    permissions: Literal['public', 'private']
    trajectory: list[dict[str, Any]] | None


FEEDBACK_URL = 'https://share-od-trajectory-3u9bw9tx.uc.gateway.dev/share_od_trajectory'


def store_feedback(feedback: FeedbackDataModel) -> dict[str, str]:
    # Start logging
    feedback.feedback = feedback.polarity
    display_feedback = feedback.model_dump()
    if 'trajectory' in display_feedback:
        display_feedback['trajectory'] = (
            f'elided [length: {len(display_feedback["trajectory"])}'
        )
    if 'token' in display_feedback:
        display_feedback['token'] = 'elided'
    logger.debug(f'Got feedback: {display_feedback}')
    config = {
        'action': 'initialize',
        'args': {
            'LLM_MODEL': os.environ['OPENHANDS_MODEL'],
            'AGENT': os.environ['OPENHANDS_AGENT'],
            'LANGUAGE': os.environ['OPENHANDS_LANGUAGE'],
        },
    }
    feedback.trajectory = [config] + feedback.trajectory if feedback.trajectory else []
    for idx in reversed(range(len(feedback.trajectory))):
        item = feedback.trajectory[idx]
        if item.get('observation') == 'agent_state_changed':
            if item.get('extras', {}).get('agent_state') in [
                'loading',
                'init',
                'running',
                'finished',
                'stopped',
            ]:
                # pop the item
                feedback.trajectory.pop(idx)
    for idx, item in enumerate(feedback.trajectory):
        if item.get('log'):
            item = {'step': item['log'].split()[-1]}
            feedback.trajectory[idx] = item
        if item.get('observation') == 'error':
            item = {'error': item['content']}
            feedback.trajectory[idx] = item
        if item.get('observation') == 'run':
            item['extras'].pop('metadata', None)
            
    # Start actual request
    response = httpx.post(
        FEEDBACK_URL,
        headers={'Content-Type': 'application/json'},
        json=feedback.model_dump(),
    )
    if response.status_code != 200:
        raise ValueError(f'Failed to store feedback: {response.text}')
    response_data: dict[str, str] = json.loads(response.text)
    logger.debug(f'Stored feedback: {response.text}')
    return response_data
