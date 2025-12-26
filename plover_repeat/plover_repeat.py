import os
from collections import deque
from datetime import datetime
from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke

class PloverRepeat:
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
    
    MEMORY_STROKE = 'PH*EPL'      # Mark/replay memory stroke
    UNDO_STROKE = '*'             # Undo stroke
    
    def __init__(self, engine: StenoEngine) -> None:
        self.engine = engine
        self.stroke_history = deque(maxlen=self.MAX_HISTORY)
        self.is_recording_memory = False
        self._processing = False
        self.debug_log = None
        
    def start(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Clear repeat_strokes.txt on startup
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write('')
            self.log(f"Cleared {self.history_file} on startup")
        except Exception as e:
            self.log(f"Error clearing history file: {e}")
        
        # Open debug log
        self.debug_log = open(self.debug_file, 'a', encoding='utf-8')
        self.log(f"=== PloverRepeat started ===")
        
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
        """Write to debug log with timestamp"""
        if self.debug_log:
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
    
    def is_memory_file_empty(self):
        """Check if memory file is empty or doesn't exist"""
        if not os.path.exists(self.memory_file):
            return True
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return len(content) == 0
        except Exception as e:
            self.log(f"Error checking memory file: {e}")
            return True
    
    def save_to_memory(self, stroke_str):
        """Save a stroke to the memory file"""
        try:
            with open(self.memory_file, 'a', encoding='utf-8') as f:
                f.write(f"{stroke_str}\n")
            self.log(f"Saved stroke to memory: {stroke_str}")
        except Exception as e:
            self.log(f"Error saving to memory: {e}")
    
    def load_and_clear_memory(self):
        """Load strokes from memory file and clear it"""
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
                
                # Clear the memory file
                with open(self.memory_file, 'w', encoding='utf-8') as f:
                    f.write('')
                self.log(f"Cleared memory file")
        except Exception as e:
            self.log(f"Error loading/clearing memory: {e}")
        
        return strokes
        
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
            
        # Check for memory stroke
        if stroke_str == self.MEMORY_STROKE:
            self.log(f"Memory stroke detected")
            # Send undo right after
            self.send_undo()
            
            # Check if memory file is empty
            if self.is_memory_file_empty():
                # Start recording to memory
                self.is_recording_memory = True
                self.log("Started recording to memory")
            else:
                # Replay memory and clear it
                self.log("Replaying memory")
                strokes = self.load_and_clear_memory()
                self.replay_strokes(strokes)
                self.is_recording_memory = False
            return
        
        # Check for undo stroke
        if stroke_str == self.UNDO_STROKE:
            # Remove the undo stroke itself
            if len(self.stroke_history) > 0:
                self.stroke_history.pop()
                self.log(f"Removed undo stroke from history")
            # Remove the stroke before it
            if len(self.stroke_history) > 0:
                removed = self.stroke_history.pop()
                self.log(f"Removed stroke from history: {removed}")
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
        self.log("Sending undo stroke to delete repeat command")
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