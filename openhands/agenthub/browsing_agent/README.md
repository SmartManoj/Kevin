# Browsing Agent Framework

This folder implements the basic BrowserGym [demo agent](https://github.com/ServiceNow/BrowserGym/tree/main/demo_agent) that enables full-featured web browsing.

# Prerequisites:
```
poetry run pip install browser-use
# Openhands depends on playwright v1.39.0 ; latest v1.51.0 ; so need to update the playwright browser
poetry run playwright install chromium
# for Gemini:
poetry run pip install langchain-google-genai 
```

## Test run

Note that for browsing tasks, GPT-4 is usually a requirement to get reasonable results, due to the complexity of the web page structures.

```
poetry run python ./openhands/core/main.py \
           -i 10 \
           -t "tell me the usa's president using google search" \
           -c BrowsingAgent \
           -l claude-3-5-sonnet-20241022
```
