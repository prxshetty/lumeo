"""Browser interaction tools."""

import webbrowser
import AppKit
import chainlit as cl
from utils.common import logger
import sys

def get_default_browser():
    try:
        # Only try to detect browser on macOS
        if sys.platform != 'darwin':
            return 'default'
            
        from AppKit import NSWorkspace, NSURL
        handler = NSWorkspace.sharedWorkspace().URLForApplicationToOpenURL_(
            NSURL.URLWithString_("http://example.com")
        )
        return handler.lastPathComponent().lower().replace(" ", "")
    except ImportError:
        logger.warning("AppKit not available, using default browser")
        return 'default'
    except Exception as e:
        logger.error(f"Error detecting default browser: {e}")
        return 'default'

open_browser_def = {
    "name": "open_browser",
    "description": "Opens a URL in the user's default web browser.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to open in the browser (e.g., 'https://example.com')",
            }
        },
        "required": ["url"],
    },
}

def open_browser_handler(url: str):
    """Open a URL in the default browser with proper error handling."""
    try:
        logger.info(f"🌐 Opening browser URL: {url}")
        
        # Try detected browser first
        browser_name = get_default_browser()
        if browser_name == "brave":
            brave_path = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'
            webbrowser.register('brave', None, webbrowser.BackgroundBrowser(brave_path))
            webbrowser.get('brave').open(url)
        else:
            webbrowser.get().open(url)
            
        return {"status": "success", "message": f"Opened {url} in browser"}
    except webbrowser.Error as e:
        logger.error(f"❌ Browser error: {str(e)}")
        return {"status": "error", "message": f"Could not open browser: {str(e)}"}
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

open_browser = (open_browser_def, open_browser_handler)
