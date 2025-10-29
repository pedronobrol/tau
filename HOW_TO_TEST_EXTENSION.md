# How to Test the VS Code Extension

## Prerequisites

1. **TAU Server must be running:**
   ```bash
   cd /Users/pedronobre/cai/dev/tau-mvp
   ./start_server.sh
   ```
   Keep this terminal open - server runs on http://localhost:8000

2. **Extension is compiled:**
   Already done! ✅

## Step-by-Step Guide

### Method 1: Open in VS Code and Press F5 (Easiest)

1. Open the `tau-vscode` folder in VS Code:
   ```bash
   cd /Users/pedronobre/cai/dev/tau-mvp/tau-vscode
   code .
   ```

2. Press `F5` (or go to Run > Start Debugging)
   - This opens a new VS Code window with the extension loaded
   - The new window will say "[Extension Development Host]" in the title

3. In the new window, open a Python file:
   ```bash
   # In the Extension Development Host window
   File > Open Folder > Navigate to /Users/pedronobre/cai/dev/tau-mvp
   # Then open examples/safe_functions.py
   ```

4. You should see:
   - **"▶ Run TAU Verification"** links above `@safe` decorators
   - Click them to verify functions!

### Method 2: Test from Terminal

If you already have VS Code open with the tau-mvp folder:

1. Make sure server is running (check http://localhost:8000)

2. Open Command Palette (`Cmd+Shift+P` on Mac, `Ctrl+Shift+P` on Windows/Linux)

3. Type: `Developer: Install Extension from Location...`

4. Select: `/Users/pedronobre/cai/dev/tau-mvp/tau-vscode`

5. Reload VS Code when prompted

6. Open `examples/safe_functions.py` and look for the "▶ Run TAU" buttons!

## What to Try

### 1. Click "Run TAU Verification"
- Open `examples/safe_functions.py`
- Look above each `@safe` decorator
- Click "▶ Run TAU Verification"
- Watch for:
  - Spinner animation while verifying
  - `✔ #hash` if successful
  - `✗` if failed
  - Error details in Problems panel (View > Problems)

### 2. Test Keyboard Shortcuts
- Place cursor on a function with `@safe`
- Press `Cmd+Shift+V` (Mac) or `Ctrl+Shift+V` (Win/Linux)
- Should trigger verification

### 3. Try Spec Generation (requires API key)
- Add to your `.env` file:
  ```bash
  ANTHROPIC_API_KEY=sk-ant-...
  ```
- Restart the TAU server
- In VS Code, type `@safe` above a function
- Press `Tab`
- Should generate `@requires` and `@ensures` with spinner!

## Troubleshooting

**"TAU server not running" warning**
- Check if server is running: `curl http://localhost:8000/`
- Start server: `./start_server.sh`

**Extension doesn't load**
- Check VS Code Output panel (View > Output > select "Extension Host")
- Look for TAU extension errors

**No "Run TAU" buttons appear**
- Make sure you're viewing a Python file
- Make sure the file has `@safe` decorators
- Try reloading the window (Cmd+R or Ctrl+R)

**Compilation errors**
```bash
cd /Users/pedronobre/cai/dev/tau-mvp/tau-vscode
npm run compile
```

## What Works Now

✅ **CodeLens** - Clickable "Run TAU" above @safe
✅ **Inline Decorations** - ✔/✗ after verification
✅ **Progress Notifications** - Shows verification progress
✅ **Diagnostics** - Failed verifications show in Problems panel
✅ **Keyboard Shortcuts** - Cmd+Shift+V to verify
⚠️ **Spec Generation** - Requires ANTHROPIC_API_KEY

## Quick Test

1. Server running? ✓
2. Open VS Code: `code /Users/pedronobre/cai/dev/tau-mvp/tau-vscode`
3. Press F5
4. Open `examples/safe_functions.py` in the new window
5. Click "▶ Run TAU Verification" above `@safe`
6. See ✔ or ✗ appear!

That's it! You're testing the extension! 🎉
