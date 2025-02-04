from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import toml


CONFIG_PATH = Path("config.toml")
TEMPLATE_PATH = Path("config.template.toml")

app = APIRouter()


@app.get("/config")
async def get_config():


    """
    Get the configuration from config.toml.
    If the file doesn't exist, read from template.
    """
    if not CONFIG_PATH.exists():
        if not TEMPLATE_PATH.exists():
            raise HTTPException(status_code=404, detail="Neither config.toml nor template exists")
        
        file_path = TEMPLATE_PATH
    else:
        file_path = CONFIG_PATH

    # read the file as toml
    config = toml.load(file_path)
    # just a textbox for the custom instructions
    html_content = f"""
    <body style="background: #508a8a;">

    <div>
        <h1>Custom Instructions</h1>
        <textarea id="custom_instructions" style="background: #d3d3c8;width: 100%; height: 100px;">
        {config['core']['custom_instructions']}
        </textarea>
        <button onclick="saveConfig()">Save</button>

    </div> """ + """
    <script>
        function saveConfig() {
            const customInstructions = document.getElementById('custom_instructions').value;
            fetch('/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ custom_instructions: customInstructions })
            }).then(response => response.json())
            .then(data => {
                alert('Config saved. Please restart the app to apply the changes.', data);
            })
            .catch(error => {
                alert('Error saving config:', error);
            });
        }
    </script>
    """ 
    try:
        return HTMLResponse(content=html_content)
    except Exception as e:
        return HTMLResponse(content=f"Error: {e}")
    

@app.post("/config")
async def save_config(data: dict):
    """
    Save the custom instructions to config.toml.
    """
    try:
        if not CONFIG_PATH.exists():
            config = {'core': {}}
        else:
            config = toml.load(CONFIG_PATH)
        config['core']['custom_instructions'] = data['custom_instructions']
        with open(CONFIG_PATH, 'w') as f:
            toml.dump(config, f)
        return {"message": "Config saved successfully"}
    except Exception as e:
        return {"message": f"Error: {e}"}, 500
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run('config_ui:app', host="0.0.0.0", port=3001, reload=True)
