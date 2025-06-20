# Thesis Defense Scheduler - Web Interface

A modern React web application for scheduling thesis defense sessions. This interface allows users to upload CSV files containing availability and request data, process them through a scheduling algorithm, and download the generated schedules.

## Features

- **File Upload**: Upload availability and request CSV files through an intuitive drag-and-drop interface
- **Processing**: Process scheduling requests with a single click
- **Results Display**: View scheduling results in organized tables
- **CSV Export**: Download generated schedules in CSV format
- **Responsive Design**: Works on desktop and mobile devices

## Project Structure

```
src/
├── App.jsx          # Main application component
├── App.css          # Application-specific styles
├── index.css        # Global styles
├── main.jsx         # Application entry point
└── assets/          # Static assets
```

## Getting Started

### Prerequisites

- Node.js (version 18 or higher)
- Python 3.8 or higher
- npm or yarn

### Quick Setup

1. **Run the setup script (recommended for beginners):**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Manual setup:**

   **Frontend:**
   ```bash
   npm install
   ```

   **Backend:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Running the Application

1. **Start the Python backend:**
   ```bash
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python app.py
   ```
   The backend will start on `http://localhost:5000`

2. **In a new terminal, start the React frontend:**
   ```bash
   npm run dev
   ```
   The frontend will start on `http://localhost:5173` or `http://localhost:5174`

3. **Open your browser** and navigate to the frontend URL

### Building for Production

```bash
npm run build
```

## Usage

1. **Upload Files**: Click on the file upload areas to select your CSV files:
   - Availability CSV: Contains lecturer availability data
   - Request CSV: Contains thesis defense requests

2. **Process**: Click the "Process" button to run the scheduling algorithm

3. **View Results**: The application will display three types of results:
   - Schedule Result: Final defense schedules
   - Timeslot Arrangement: Time slot utilization
   - Examiner Schedule: Individual examiner schedules

4. **Download**: Click the "Download CSV" buttons to export results

## File Formats

### Availability CSV
Expected columns based on config:
- Lecturer name and expertise information
- Time slot availability data

### Request CSV  
Expected columns based on config:
- Student information (name, ID)
- Field of study information
- Supervisor information
- Capstone project details

## Integration with Python Backend

This React application now includes a Flask backend that integrates with your existing Python scheduling code.

### Backend Architecture

- **Flask API**: Handles file uploads and communicates with your Python scheduler
- **File Processing**: Converts uploaded CSV files and calls your scheduling algorithm
- **Results API**: Returns processed results as JSON and provides CSV downloads

### Python Code Integration

The backend automatically tries to integrate with your Python scheduling code located in:
```
../../../src/main.py  # Your main scheduling script
```

The integration works by:
1. Receiving CSV files from the React frontend
2. Saving them temporarily with the expected filenames (`avail.csv`, `req.csv`)
3. Creating a temporary config file
4. Running your Python scheduling code
5. Reading the generated results and returning them to the frontend

### File Structure
```
ui/react_app/
├── backend/           # Flask backend
│   ├── app.py        # Main Flask application
│   ├── requirements.txt
│   ├── uploads/      # Temporary upload folder
│   └── outputs/      # Generated results
├── src/              # React frontend
└── README.md
```

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Technology Stack

- **React 18** - Frontend framework
- **Vite** - Build tool and development server
- **Modern CSS** - Styling with CSS Grid and Flexbox
- **ESLint** - Code linting

## Future Enhancements

- Real-time processing updates
- Integration with backend API
- Advanced filtering and sorting of results
- User authentication and session management
- Conflict resolution interface
- Export to multiple formats (PDF, Excel)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request+ Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
