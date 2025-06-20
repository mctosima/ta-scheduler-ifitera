# Flask Backend for Thesis Defense Scheduler

This Flask backend serves as a bridge between your React frontend and your Python scheduling code.

## Setup

1. **Create and activate a Python virtual environment:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Flask server:**
   ```bash
   python app.py
   ```

The server will start on `http://localhost:5000`

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/upload` - Upload CSV files and process scheduling
- `GET /api/download/<filename>` - Download result files

## How it works

1. **File Upload**: Receives availability and request CSV files from the React frontend
2. **Processing**: Calls your Python scheduling code located in the parent directory
3. **Results**: Returns the generated schedules as JSON and provides download links for CSV files

## Integration with your Python code

The backend tries to import your scheduling modules directly. If that fails, it falls back to running your `main.py` script as a subprocess. 

Make sure your Python scheduling code is located at:
- `../../../src/main.py` (relative to this backend directory)

## File Structure

```
backend/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── uploads/           # Temporary upload folder
├── outputs/           # Generated results folder
└── venv/              # Virtual environment (created after setup)
```

## Troubleshooting

1. **Import errors**: If the backend can't import your scheduling modules, it will fall back to subprocess execution
2. **File paths**: Make sure your Python scheduling code is in the expected location
3. **Dependencies**: Ensure all your scheduling code dependencies are installed in the virtual environment

## Development

- The Flask server runs in debug mode for development
- CORS is enabled to allow requests from the React frontend
- File uploads are validated to ensure only CSV files are accepted
