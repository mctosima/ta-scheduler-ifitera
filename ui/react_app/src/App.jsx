import { useState } from 'react'
import './App.css'

function App() {
  const [availabilityFile, setAvailabilityFile] = useState(null)
  const [requestFile, setRequestFile] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [results, setResults] = useState(null)

  const handleFileUpload = (event, fileType) => {
    const file = event.target.files[0]
    if (file && file.type === 'text/csv') {
      if (fileType === 'availability') {
        setAvailabilityFile(file)
      } else if (fileType === 'request') {
        setRequestFile(file)
      }
    } else {
      alert('Please upload a valid CSV file')
    }
  }

  const handleProcess = async () => {
    if (!availabilityFile || !requestFile) {
      alert('Please upload both availability and request CSV files')
      return
    }

    setIsProcessing(true)
    
    try {
      // Create FormData to send files
      const formData = new FormData()
      formData.append('availability', availabilityFile)
      formData.append('request', requestFile)
      
      // Send files to Flask backend
      console.log('Sending request to backend...')
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      })
      console.log('Response received:', response.status, response.statusText)
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Processing failed')
      }
      
      const results = await response.json()
      console.log('Results received:', results)
      setResults(results)
      
    } catch (error) {
      console.error('Error processing files:', error)
      alert(`Error: ${error.message}`)
      setResults(null) // Clear results on error instead of showing mock data
    } finally {
      setIsProcessing(false)
    }
  }

  const downloadCSV = async (data, filename, backendFilename = null) => {
    try {
      if (backendFilename) {
        // Download from Flask backend
        const response = await fetch(`http://localhost:8000/api/download/${backendFilename}`)
        if (response.ok) {
          const blob = await response.blob()
          const url = window.URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = filename
          link.click()
          window.URL.revokeObjectURL(url)
          return
        }
      }
      
      // Fallback to client-side CSV generation
      if (!data || data.length === 0) return
      
      const headers = Object.keys(data[0]).join(',')
      const rows = data.map(row => Object.values(row).join(','))
      const csvContent = [headers, ...rows].join('\n')
      
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.URL.revokeObjectURL(url)
      
    } catch (error) {
      console.error('Download failed:', error)
      alert('Download failed. Please try again.')
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Thesis Defense Scheduler</h1>
        <p>Upload your availability and request files to generate optimal scheduling</p>
      </header>

      <main className="app-main">
        {/* File Upload Section */}
        <section className="upload-section">
          <h2>Upload Files</h2>
          <div className="upload-container">
            <div className="file-upload">
              <label htmlFor="availability-file">
                <span className="upload-label">Availability CSV</span>
                <input
                  id="availability-file"
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleFileUpload(e, 'availability')}
                />
                <div className="file-info">
                  {availabilityFile ? (
                    <span className="file-selected">✓ {availabilityFile.name}</span>
                  ) : (
                    <span className="file-placeholder">Choose availability file...</span>
                  )}
                </div>
              </label>
            </div>

            <div className="file-upload">
              <label htmlFor="request-file">
                <span className="upload-label">Request CSV</span>
                <input
                  id="request-file"
                  type="file"
                  accept=".csv"
                  onChange={(e) => handleFileUpload(e, 'request')}
                />
                <div className="file-info">
                  {requestFile ? (
                    <span className="file-selected">✓ {requestFile.name}</span>
                  ) : (
                    <span className="file-placeholder">Choose request file...</span>
                  )}
                </div>
              </label>
            </div>
          </div>

          <button 
            className="process-button"
            onClick={handleProcess}
            disabled={!availabilityFile || !requestFile || isProcessing}
          >
            {isProcessing ? 'Processing...' : 'Process'}
          </button>
        </section>

        {/* Results Section */}
        {results && (
          <section className="results-section">
            <h2>Scheduling Results</h2>
            
            <div className="results-container">
              {/* Schedule Result */}
              <div className="result-card">
                <div className="result-header">
                  <h3>Schedule Result</h3>
                  <button 
                    className="download-button"
                    onClick={() => downloadCSV(results.scheduleResult, 'schedule_result.csv', 'final_output.csv')}
                  >
                    Download CSV
                  </button>
                </div>
                <div className="result-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>NIM</th>
                        <th>Date</th>
                        <th>Time</th>
                        <th>Examiner 1</th>
                        <th>Examiner 2</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.scheduleResult.map((row, index) => (
                        <tr key={index}>
                          <td>{row.nama}</td>
                          <td>{row.nim}</td>
                          <td>{row.Date}</td>
                          <td>{row['Start Time']} - {row['End Time']}</td>
                          <td>{row.examiner_1}</td>
                          <td>{row.examiner_2}</td>
                          <td>{row.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Timeslot Arrangement */}
              <div className="result-card">
                <div className="result-header">
                  <h3>Timeslot Arrangement</h3>
                  <button 
                    className="download-button"
                    onClick={() => downloadCSV(results.timeslotArrangement, 'timeslot_arrangement.csv', 'final_timeslot.csv')}
                  >
                    Download CSV
                  </button>
                </div>
                <div className="result-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Time</th>
                        <th>Slot A</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.timeslotArrangement.map((row, index) => (
                        <tr key={index}>
                          <td>{row.Date}</td>
                          <td>{row.time}</td>
                          <td>{row.slot_A}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Examiner Schedule */}
              <div className="result-card">
                <div className="result-header">
                  <h3>Examiner Schedule</h3>
                  <button 
                    className="download-button"
                    onClick={() => downloadCSV(results.examinerSchedule, 'examiner_schedule.csv', 'final_lectureschedule.csv')}
                  >
                    Download CSV
                  </button>
                </div>
                <div className="result-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Name</th>
                        <th>Total Scheduled</th>
                        <th>Schedule</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.examinerSchedule.map((row, index) => (
                        <tr key={index}>
                          <td>{row.CODE}</td>
                          <td>{row.Nama}</td>
                          <td>{row['Total Dijadwalkan']}</td>
                          <td>{row.Jadwal}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
