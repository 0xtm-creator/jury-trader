import uvicorn
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api.server import app
PORT = 8002
uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
