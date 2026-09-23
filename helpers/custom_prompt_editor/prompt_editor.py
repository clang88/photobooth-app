#!/usr/bin/env python3
"""
Lightweight HTTP server for editing photobooth prompts.
Usage: python prompt_editor.py [port]
Default port: 8080
"""

import http.server
import json
import os
import socketserver
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Get the project root directory (parent of opt/)
PROJECT_ROOT = Path(__file__).parent.parent

# Plugin prompt directories - each plugin has its own custom_prompt folder
PLUGIN_PROMPT_DIRS = {
    "filter_nanobanana": PROJECT_ROOT / "plugins" / "filter_nanobanana" / "custom_prompt",
    "filter_openai": PROJECT_ROOT / "plugins" / "filter_openai" / "custom_prompt",
}

# Default plugin
DEFAULT_PLUGIN = "filter_nanobanana"


def get_prompt_file(plugin_name: str) -> Path:
    """Get the prompt.txt path for a given plugin."""
    return PLUGIN_PROMPT_DIRS.get(plugin_name, PLUGIN_PROMPT_DIRS[DEFAULT_PLUGIN])


def get_history_file(plugin_name: str) -> Path:
    """Get the history file path for a given plugin."""
    return PROJECT_ROOT / "photobooth-data" / "config" / "prompts" / f"{plugin_name}_prompts_history.txt"


# Ensure directories exist
for path in PLUGIN_PROMPT_DIRS.values():
    path.mkdir(parents=True, exist_ok=True)

# HTML template with embedded JavaScript and CSS
HTML_TEMPLATE = open(Path(__file__).parent / "prompt_editor_html_template.html").read()


class PromptEditorHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for the prompt editor."""

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/" or parsed_path.path == "/index.html":
            # Serve the main HTML page
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
            
        elif parsed_path.path == "/api/prompts":
            # Return current prompt and history for selected plugin
            query_params = parse_qs(parsed_path.query)
            plugin_name = query_params.get("plugin", [DEFAULT_PLUGIN])[0]
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            prompt_file = get_prompt_file(plugin_name)
            history_file = get_history_file(plugin_name)
            
            current_prompt = ""
            if prompt_file.exists():
                current_prompt = prompt_file.read_text()
            
            history = []
            if history_file.exists():
                lines = history_file.read_text().strip().split("\n")
                for line in lines:
                    if line.strip():
                        parts = line.split("|||", 1)
                        if len(parts) == 2:
                            history.append({
                                "timestamp": parts[0].strip(),
                                "text": parts[1].strip()
                            })
                        else:
                            # Continuation of previous prompt
                            if history:
                                history[-1]["text"] += "\n" + line.strip()
            
            # Reverse to show newest first
            history.reverse()
            
            response = {
                "current": current_prompt,
                "history": history,
                "plugin": plugin_name,
                "available_plugins": list(PLUGIN_PROMPT_DIRS.keys())
            }
            
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/api/update":
            # Read POST data
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                prompt = data.get("prompt", "").strip()
                plugin_name = data.get("plugin", DEFAULT_PLUGIN)
                
                if not prompt:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "Empty prompt"}).encode())
                    return
                
                # Ensure plugin is valid
                if plugin_name not in PLUGIN_PROMPT_DIRS:
                    plugin_name = DEFAULT_PLUGIN
                
                # Save to current prompt file for the selected plugin
                prompt_file = get_prompt_file(plugin_name)
                prompt_file.write_text(prompt)
                
                # Append to history with timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                history_entry = f"{timestamp} ||| {prompt}\n"
                
                history_file = get_history_file(plugin_name)
                with open(history_file, "a") as f:
                    f.write(history_entry)
                
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
                
                print(f"[{timestamp}] Prompt updated for {plugin_name}: {prompt[:50]}...")
                
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
                print(f"Error: {e}")
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        """Override to customize logging."""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(port=8001):
    """Start the HTTP server."""
    with socketserver.TCPServer(("", port), PromptEditorHandler) as httpd:
        print(f"🚀 Prompt Editor Server running at http://localhost:{port}")
        print(f"📝 Prompt file: {PROMPT_FILE}")
        print(f"📚 History file: {HISTORY_FILE}")
        print("Press Ctrl+C to stop the server")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped")


if __name__ == "__main__":
    import sys
    
    port = 8001
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    run_server(port)
