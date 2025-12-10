# OpenAI Integration for Transcription and Notes Generation

## Overview
This implementation adds automatic transcription and notes generation using OpenAI after a broadcast completes. The system automatically transcribes the audio and generates study notes, with status tracking and download capabilities.

## Features Implemented

### 1. Automatic Transcription
- After a broadcast ends, the system automatically transcribes the audio using OpenAI's Whisper model
- Transcription status is tracked (processing, completed, failed)
- Transcripts are saved to the database and as text files

### 2. Automatic Notes Generation
- After transcription completes, the system automatically generates comprehensive study notes using OpenAI GPT-4o-mini
- Notes include:
  - Brief summary
  - Key concepts and main points
  - Important details and examples
  - Formulas, definitions, and important facts

### 3. Status Tracking
- Real-time status updates for both transcription and notes generation
- Status displayed in a modal after broadcast completion
- Polling mechanism to check status every 5 seconds

### 4. Download Functionality
- **Transcripts**: Download as `.txt` files
- **Notes**: Download as `.pdf` files (with text fallback if PDF generation fails)

## Setup Instructions

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

The following packages have been added:
- `openai==1.54.3` - For transcription and notes generation
- `reportlab==4.2.2` - For PDF generation
- `python-dotenv==1.0.1` - For environment variable management

### 2. Set Up OpenAI API Key
Create a `.env` file in the `backend` directory (if it doesn't exist) and add:
```
OPENAI_API_KEY=your_openai_api_key_here
```

You can get your API key from: https://platform.openai.com/api-keys

### 3. Run the Application
```bash
cd backend
python app.py
```

## API Endpoints Added

### Get Broadcast Status
```
GET /api/broadcasts/<broadcast_id>/status
```
Returns the status of transcription and notes generation for a broadcast.

**Response:**
```json
{
  "success": true,
  "broadcast_id": 1,
  "transcription": {
    "exists": true,
    "status": "completed",
    "id": 1
  },
  "notes": {
    "exists": true,
    "status": "completed",
    "id": 1
  }
}
```

### Manually Trigger Transcription
```
POST /api/broadcasts/<broadcast_id>/transcribe
```
Manually triggers transcription for a broadcast (if not already completed).

### Manually Trigger Notes Generation
```
POST /api/broadcasts/<broadcast_id>/generate-notes
```
Manually triggers notes generation for a broadcast (requires completed transcription).

### Get Transcript
```
GET /api/broadcasts/<broadcast_id>/transcript
```
Returns the transcript for a broadcast.

### Download Transcript
```
GET /api/broadcasts/<broadcast_id>/transcript/download
```
Downloads the transcript as a text file.

### Get Notes
```
GET /api/broadcasts/<broadcast_id>/notes
```
Returns the notes for a broadcast.

### Download Notes (PDF)
```
GET /api/broadcasts/<broadcast_id>/notes/download
```
Downloads the notes as a PDF file (falls back to text if PDF generation fails).

## User Flow

### For Teachers:
1. Start a broadcast as usual
2. When the broadcast ends, a modal automatically appears showing:
   - Transcription status (Processing → Completed)
   - Notes generation status (Waiting → Processing → Completed)
   - Progress bar showing overall completion
3. Once both are completed, download buttons appear:
   - Download Transcript (as .txt)
   - Download Notes (as .pdf)

### For Students/Admins:
- View transcripts in the admin transcripts page
- Download transcripts and notes from the broadcast details

## File Structure

### Backend Changes:
- `backend/app.py`: Added transcription and notes generation functions, new API endpoints
- `backend/requirements.txt`: Added OpenAI and ReportLab dependencies

### Frontend Changes:
- `theme/live-broadcasting.html`: Added status modal and download functionality
- `static/js/api.js`: Added API methods for status and downloads

## Technical Details

### Transcription Process:
1. When broadcast ends, `transcribe_broadcast_audio()` is called in a background thread
2. Audio file is read and sent to OpenAI Whisper API
3. Transcript is saved to database and as a text file
4. Notes generation is automatically triggered after transcription completes

### Notes Generation Process:
1. After transcription completes, `generate_broadcast_notes()` is called
2. Transcript is sent to OpenAI GPT-4o-mini with a prompt to create study notes
3. Notes are saved to database and as a text file
4. PDF is generated on-demand when user downloads

### Error Handling:
- If OpenAI API is unavailable, errors are logged and status is set to "failed"
- If PDF generation fails, notes are downloaded as text files
- Background threads handle processing without blocking the main application

## Notes

- Transcription uses OpenAI's `whisper-1` model
- Notes generation uses OpenAI's `gpt-4o-mini` model
- All processing happens in background threads to avoid blocking
- Status updates are sent via WebSocket events
- Files are stored in `uploads/transcriptions/` and `uploads/notes/` directories

## Troubleshooting

### Transcription Not Starting:
- Check that `OPENAI_API_KEY` is set in `.env` file
- Verify the audio file exists at the path stored in the database
- Check backend logs for error messages

### Notes Not Generating:
- Ensure transcription completed successfully
- Check OpenAI API key and quota
- Verify the transcript content is not empty

### PDF Download Fails:
- System automatically falls back to text file download
- Check that ReportLab is installed: `pip install reportlab`

## Future Enhancements

Possible improvements:
- Support for multiple languages in transcription
- Customizable note templates
- Batch processing for multiple broadcasts
- Email notifications when processing completes
- Real-time progress updates via WebSocket


