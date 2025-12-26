import os
from collections import deque
from datetime import datetime
from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke

class PloverRepeat:
    # ===== DEBUG TOGGLE - Set to False to disable all debug logging =====
    DEBUG_ENABLED = True
    # ====================================================================
    
    history_file = os.path.join(CONFIG_DIR, 'repeat_strokes.txt')
    debug_file = os.path.join(CONFIG_DIR, 'repeat_debug.txt')
    memory_file = os.path.join(CONFIG_DIR, 'repeat_memory.txt')
    MAX_HISTORY = 100
    
    # Binary repeat mappings (right hand: -FPLTD)
    REPEAT_STROKES = {
        'RA*PT': 1, 'RO*PT': 2, 'RAO*PT': 3, 'R*EPT': 4, 'RA*EPT': 5,
        'RO*EPT': 6, 'RAO*EPT': 7, 'R*UPT': 8, 'RA*UPT': 9, 'RO*UPT': 10,
        'RAO*UPT': 11, 'R*EUPT': 12, 'RA*EUPT': 13, 'RO*EUPT': 14, 'RAO*EUPT': 15,
    }
    
    MEMORY_TOGGLE_STROKE = 'PO*FP'   # Toggle logging to memory
    MEMORY_PASTE_STROKE = 'SKWR*PL'   # Paste memory contents
    MEMORY_RESET_STROKE = 'R*ET'   # Reset and clear memory
    UNDO_STROKE = '*'                  # Undo stroke
    
    def __init__(self, engine: StenoEngine) -> None:
        self.engine = engine
        self.stroke_history = deque(maxlen=self.MAX_HISTORY)
        self.is_recording_memory = False
        self._processing = False
        self.debug_log = None
        
    def start(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Open debug log only if debugging is enabled
        if self.DEBUG_ENABLED:
            self.debug_log = open(self.debug_file, 'a', encoding='utf-8')
            self.log(f"=== PloverRepeat started ===")
        
        # Clear repeat_strokes.txt on startup
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write('')
            self.log(f"Cleared {self.history_file} on startup")
        except Exception as e:
            self.log(f"Error clearing history file: {e}")
        
        self.engine.hook_connect('stroked', self.on_stroked)
        self.load_history()
        self.log(f"Loaded {len(self.stroke_history)} strokes from history")
        
    def stop(self) -> None:
        self.log(f"=== PloverRepeat stopped ===")
        self.engine.hook_disconnect('stroked', self.on_stroked)
        self.save_history()
        if self.debug_log:
            self.debug_log.close()
            self.debug_log = None
    
    def log(self, message):
        """Write to debug log with timestamp (only if debugging enabled)"""
        if self.DEBUG_ENABLED and self.debug_log:
            timestamp = datetime.now().strftime('%F %T')
            self.debug_log.write(f"[{timestamp}] {message}\n")
            self.debug_log.flush()
        
    def load_history(self):
        """Load stroke history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        stroke = line.strip()
                        if stroke:
                            self.stroke_history.append(stroke)
                self.log(f"Loaded {len(lines)} strokes from {self.history_file}")
        except Exception as e:
            self.log(f"Error loading history: {e}")
        
    def save_history(self):
        """Save stroke history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for stroke in self.stroke_history:
                    f.write(f"{stroke}\n")
            self.log(f"Saved {len(self.stroke_history)} strokes to {self.history_file}")
        except Exception as e:
            self.log(f"Error saving history: {e}")
    
    def save_history_live(self):
        """Save history immediately (live updates)"""
        self.save_history()
    
    def save_to_memory(self, stroke_str):
        """Save a stroke to the memory file"""
        try:
            with open(self.memory_file, 'a', encoding='utf-8') as f:
                f.write(f"{stroke_str}\n")
            self.log(f"Saved stroke to memory: {stroke_str}")
        except Exception as e:
            self.log(f"Error saving to memory: {e}")
    
    def load_memory(self):
        """Load strokes from memory file without clearing"""
        strokes = []
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        stroke = line.strip()
                        if stroke:
                            strokes.append(stroke)
                self.log(f"Loaded {len(strokes)} strokes from memory")
        except Exception as e:
            self.log(f"Error loading memory: {e}")
        
        return strokes
    
    def clear_memory(self):
        """Clear the memory file"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                f.write('')
            self.log(f"Cleared memory file")
        except Exception as e:
            self.log(f"Error clearing memory: {e}")
        
    def on_stroked(self, stroke: Stroke):
        if self._processing:
            return
            
        stroke_str = stroke.rtfcre
        self.log(f"Received stroke: {stroke_str}")
        
        # Check for repeat commands
        if stroke_str in self.REPEAT_STROKES:
            n = self.REPEAT_STROKES[stroke_str]
            self.log(f"Repeat command detected: repeat last {n} strokes")
            # Delete the repeat command stroke itself FIRST
            self.send_undo()
            # Then repeat the strokes
            self.repeat_last_n(n)
            return
            
        # Check for memory toggle stroke
        if stroke_str == self.MEMORY_TOGGLE_STROKE:
            self.log(f"Memory toggle stroke detected")
            # Send undo right after
            self.send_undo()
            
            # Toggle recording state
            self.is_recording_memory = not self.is_recording_memory
            if self.is_recording_memory:
                self.log("Started recording to memory")
            else:
                self.log("Stopped recording to memory")
            return
        
        # Check for memory paste stroke
        if stroke_str == self.MEMORY_PASTE_STROKE:
            self.log(f"Memory paste stroke detected")
            # Send undo right after
            self.send_undo()
            
            # Load and replay memory
            strokes = self.load_memory()
            self.replay_strokes(strokes)
            return
        
        # Check for memory reset stroke
        if stroke_str == self.MEMORY_RESET_STROKE:
            self.log(f"Memory reset stroke detected")
            # Send undo right after
            self.send_undo()
            
            # Clear memory file
            self.clear_memory()
            self.is_recording_memory = False
            self.log("Memory cleared and recording stopped")
            return
        
        # Check for undo stroke
        if stroke_str == self.UNDO_STROKE:
            # Remove the stroke before the undo (from history)
            if len(self.stroke_history) > 0:
                removed = self.stroke_history.pop()
                self.log(f"Removed stroke from history due to undo: {removed}")
                self.save_history_live()
            return
        
        # If recording to memory, save this stroke
        if self.is_recording_memory:
            self.save_to_memory(stroke_str)
            
        # Record stroke in history (if not a repeat command)
        self.stroke_history.append(stroke_str)
        self.save_history_live()
        self.log(f"Stroke added to history. Total: {len(self.stroke_history)}")
    
    def send_undo(self):
        """Send an undo stroke to delete the previous output"""
        self.log("Sending undo stroke to delete command")
        self._processing = True
        try:
            undo_stroke = Stroke.from_steno(self.UNDO_STROKE)
            self.engine._machine_stroke_callback(undo_stroke)
            self.log("Undo stroke sent")
        except Exception as e:
            self.log(f"Error sending undo: {e}")
        finally:
            self._processing = False
    
    def replay_strokes(self, strokes):
        """Replay a list of strokes"""
        self.log(f"Replaying {len(strokes)} strokes: {strokes}")
        
        self._processing = True
        try:
            for stroke_str in strokes:
                stroke = Stroke.from_steno(stroke_str)
                self.engine._machine_stroke_callback(stroke)
                self.log(f"Replayed stroke: {stroke_str}")
        except Exception as e:
            self.log(f"Error replaying strokes: {e}")
        finally:
            self._processing = False
        
    def repeat_last_n(self, n):
        """Repeat the last n strokes"""
        if n > len(self.stroke_history):
            self.log(f"Cannot repeat {n} strokes, only {len(self.stroke_history)} in history")
            return
            
        strokes_to_repeat = list(self.stroke_history)[-n:]
        self.replay_strokes(strokes_to_repeat)