from enum import Enum

from pydantic import BaseModel, Field, model_serializer
from typing_extensions import Literal

from opendevin.core.config import load_app_config

config = load_app_config()


class ContentType(Enum):
    TEXT = 'text'
    IMAGE_URL = 'image_url'


class Content(BaseModel):
    type: ContentType

    @model_serializer
    def serialize_model(self):
        raise NotImplementedError('Subclasses should implement this method.')


class TextContent(Content):
    text: str
    type: ContentType = ContentType.TEXT

    @model_serializer
    def serialize_model(self):
        return {'type': self.type.value, 'text': self.text}


class ImageContent(Content):
    image_urls: list[str]
    type: ContentType = ContentType.IMAGE_URL

    @model_serializer
    def serialize_model(self):
        images: list[dict[str, str | dict[str, str]]] = []
        for url in self.image_urls:
            images.append({'type': self.type.value, 'image_url': {'url': url}})
        return images


class Message(BaseModel):
    role: Literal['user', 'system', 'assistant']
    content: list[TextContent | ImageContent] = Field(default=list)
    condensable: bool = True
    event_id: int = -1

    @property
    def contains_image(self) -> bool:
        return any(isinstance(content, ImageContent) for content in self.content)

    @model_serializer
    def serialize_model(self) -> dict:
        content: list[dict[str, str | dict[str, str]]] = []
        # check model provider is groq
        if 'groq/' in config.get_llm_config().model:
            if self.role in ['system', 'assistant']:
                return {'role': self.role, 'content': self.content[0].text}

        # TODO: check whether the model supports vision
        if 'ollama/' in config.get_llm_config().model:
            text_contents = '\n'.join([item.text for item in self.content])
            return {'role': self.role, 'content': text_contents}

        for item in self.content:
            if isinstance(item, TextContent):
                content.append(item.model_dump())
            elif isinstance(item, ImageContent):
                content.extend(item.model_dump())

        return {'role': self.role, 'content': content}
