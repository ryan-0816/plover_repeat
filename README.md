# PloverRepeat

A Plover plugin that provides powerful stroke history management and repetition capabilities for stenography.

## Features

### 1. Repeat Last N Strokes
Quickly repeat the last 1-15 strokes you typed using binary-encoded shorthand commands.

### 2. Memory Recording & Playback
Record a sequence of strokes and replay them repeatedly on the go

## Stroke Commands

### Binary Repeat (1-15 strokes)
Base stroke is `R*PT`, then `AOEU` as binary for how far back you want to repeat, up to 15.

| Stroke   | Value | Stroke    | Value | Stroke     | Value |
| -------- | ----- | --------- | ----- | ---------- | ----- |
| `RA*PT`  | 1     | `RO*EPT`  | 6     | `RAO*UPT`  | 11    |
| `RO*PT`  | 2     | `RAO*EPT` | 7     | `R*EUPT`   | 12    |
| `RAO*PT` | 3     | `R*UPT`   | 8     | `RA*EUPT`  | 13    |
| `R*EPT`  | 4     | `RA*UPT`  | 9     | `RO*EUPT`  | 14    |
| `RA*EPT` | 5     | `RO*UPT`  | 10    | `RAO*EUPT` | 15    |


**Example:** Type "hello there" then stroke `RO*PT` to output "hello there" again.

### Memory Commands

| Stroke | Function |
|--------|----------|
| `PO*FP` | Toggle memory recording on/off |
| `SKWR*PL` | Paste (replay) recorded memory |
| `R*ET` | Reset and clear memory |

**Example Workflow:**
1. Stroke `PO*FP` to start recording
2. Type your template text
3. Stroke `PO*FP` again to stop recording
4. Use `SKWR*PL` anytime to replay the template
5. Use `R*ET` to clear when you want to record something new

## Configuration

### Debug Mode
To enable or disable debug logging, edit the top of the file:

```python
# Set to True to enable debug logging, False to disable
DEBUG_ENABLED = True
```

Debug logs are written to `repeat_debug.txt` in your Plover config directory.

### File Locations
All files are stored in your Plover config directory:
- `repeat_strokes.txt` - Stroke history (cleared on startup)
- `repeat_memory.txt` - Recorded memory sequences
- `repeat_debug.txt` - Debug log (if enabled)

## Tips

- The repeat commands don't include themselves in the count - they only repeat actual content strokes
- Memory recording can be toggled on and off multiple times - it appends to the existing memory
- Use `R*ET` to start fresh with a new memory sequence
- History is cleared on plugin startup