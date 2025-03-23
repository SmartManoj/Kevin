# Browser Use Agent Framework

This folder integrates the [browser-use](https://github.com/browser-use/browser-use) framework that enables full-featured web browsing.

# Prerequisites:
```
poetry run pip install browser-use
# Openhands depends on playwright v1.39.0 ; latest v1.51.0 ; so need to update the playwright browser
poetry run playwright install chromium
# for Gemini:
poetry run pip install langchain-google-genai 
```

## Test run

```
poetry run python ./openhands/core/main.py \
           -i 10 \
           -t "tell me the usa's president using google search" \
           -c BrowserUseAgent 
```
