# PortAI

PortAI is a Windows desktop voice assistant that runs from a lightweight system-tray app. Hold `Ctrl+Alt` to record a request, then release the keys to have PortAI transcribe and route it. Responses appear in an animated on-screen drawer.

> **Current architecture:** Speech transcription runs locally with Faster-Whisper. Intent classification, chat responses, clipboard analysis, and screenshot analysis use the Nebius API, so an internet connection and a Nebius API key are required. PortAI is not fully offline, and it is not currently packaged as a portable USB application.

## Features

- Voice input with local Faster-Whisper transcription. CUDA is used when available; otherwise transcription falls back to the CPU.
- AI chat and follow-up context, with an option to clear the conversation.
- Screen analysis using a screenshot of the current desktop.
- Clipboard description and summarization for text copied to the clipboard.
- Launching an allowlisted set of Windows apps: VS Code, Notepad, Calculator, File Explorer, Terminal, Command Prompt, PowerShell, Chrome, Firefox, and Edge.
- Countdown timers and reminders delivered as Windows notifications (up to seven days).
- Task creation, listing, completion, and deletion, stored in a local SQLite database.
- System-tray controls, a floating status pill, and an animated response drawer.

## Project Presentation

----------

## Requirements

- Windows 10 or later.
- Python 3.10 or later; Python 3.12 is the version used during development.
- A working microphone and internet connection.
- A Nebius API key with access to the configured chat models.
- Optional: a CUDA-capable GPU for faster local transcription. CPU transcription is supported but may be slower.

The first launch may download the Faster-Whisper model. Allow access to the microphone and permit network access for Nebius API requests and model downloads.

## Setup

Run these commands from the project root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The frozen `requirements.txt` includes the app's runtime packages, including `PyQt6` and `winotify`. If PowerShell blocks virtual-environment activation, run `\.\.venv\Scripts\python.exe -m pip install -r requirements.txt` from the project root instead.

Open `.env` and replace the example value with your Nebius API key:

```dotenv
NEBIUS_API_KEY=your_nebius_api_key
```

Do not commit `.env` or share your API key. The repository ignores `.env`; `.env.example` is only a placeholder.

## Run

From the project root, with the virtual environment active:

```powershell
python src\integration.py
```

The assistant starts in the system tray. Hold `Ctrl+Alt` while speaking and release the keys when you are done. Choose **Toggle Side Drawer**, **Clear Context**, or **Exit PortAI** from the tray menu.

## Example Requests

- "Summarize my clipboard" or "What's in my clipboard?"
- "What is on my screen?"
- "Open Notepad."
- "Set a timer for 10 minutes."
- "Remind me to stretch in 30 minutes."
- "Add a task to review the project README."
- "List my tasks" or "List my reminders."

Task completion and deletion, and reminder cancellation, require the corresponding ID returned by PortAI.

## Project Layout

```text
src/
	integration.py          Desktop app entry point, hotkey, tray, and worker thread
	backend/
		ai_core.py             Whisper recording/transcription and Nebius API calls
		task_router.py         Intent classification and action dispatch
	integrations/
		apps.py                Allowlisted Windows application launching
		clipboard.py           Clipboard text retrieval and AI analysis
		reminders.py           In-memory timers and Windows notifications
		tasks.py               SQLite-backed task management
	ui/
		widgets.py             Floating pill, screen glow, response drawer, tray icon
data/
	portai.db                Created automatically for task storage
.env                       Local Nebius API key (create from .env.example)
requirements.txt           Frozen package versions from the project environment
```

## Troubleshooting
- Microphone does not start: Confirm that Windows has granted microphone permission and that a recording device is selected.
- API request fails: Confirm that NEBIUS_API_KEY is present in .env and that the key is valid.
- Whisper loads slowly on the first run: Faster Whisper may need to download its model files.
- CUDA initialization fails: PortAI automatically falls back to the CPU base Whisper model.
- Application does not launch an app: Confirm that the requested program is installed and available on Windows.

## Data and Privacy

- Microphone audio is transcribed locally; the resulting request text is sent to Nebius for classification and, when needed, response generation.
- Clipboard text is sent to Nebius when a clipboard action is requested. Clipboard input is limited to 12,000 characters before analysis.
- A screenshot is captured and sent to Nebius when screen analysis is requested.
- Conversation history and active timers/reminders are held in memory and are cleared when the app exits. Task records persist in `data/portai.db`.
- Avoid sending sensitive information through chat, clipboard analysis, or screen analysis unless you are comfortable with the configured API provider processing it.

## Team Members

The following are the contributors:

- Prajwal-747
- 555Rajeev_srk
- abhirampreddy546-droid
- likithab0211-blip
- idskg

