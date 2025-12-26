import os
from collections import deque
from datetime import datetime
from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke

class PloverRepeat:
    history_file = os.path.join(CONFIG_DIR, 'repeat_strokes.txt')
    debug_file = os.path.join(CONFIG_DIR, 'repeat_debug.txt')
    MAX_HISTORY = 100
    
    # Binary repeat mappings (right hand: -FPLTD)
    REPEAT_STROKES = {
        'RA*PT': 1, 'RO*PT': 2, 'RAO*PT': 3, 'R*EPT': 4, 'RA*EPT': 5,
        'RO*EPT': 6, 'RAO*EPT': 7, 'R*UPT': 8, 'RA*UPT': 9, 'RO*UPT': 10,
        'RAO*UPT': 11, 'R*EUPT': 12, 'RA*EUPT': 13, 'RO*EUPT': 14, 'RAO*EUPT': 15,
    }
    
    MARK_STROKE = 'PHA*RBG'      # Mark current position
    REPEAT_TO_STROKE = 'REP/TO'  # Repeat from mark to current
    UNDO_STROKE = '*'             # Undo stroke
    
    def __init__(self, engine: StenoEngine) -> None:
        self.engine = engine
        self.stroke_history = deque(maxlen=self.MAX_HISTORY)
        self.mark_position = None
        self._processing = False
        self.debug_log = None
        
    def start(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
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
            
        # Check for mark
        if stroke_str == self.MARK_STROKE:
            self.mark_position = len(self.stroke_history)
            self.log(f"Mark set at position {self.mark_position}")
            return
            
        # Check for repeat-to-mark
        if stroke_str == self.REPEAT_TO_STROKE:
            self.log(f"Repeat-to-mark command detected")
            # Delete the repeat-to-mark command stroke itself FIRST
            self.send_undo()
            # Then repeat from mark
            self.repeat_from_mark()
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
        
    def repeat_last_n(self, n):
        """Repeat the last n strokes"""
        if n > len(self.stroke_history):
            self.log(f"Cannot repeat {n} strokes, only {len(self.stroke_history)} in history")
            return
            
        strokes_to_repeat = list(self.stroke_history)[-n:]
        self.log(f"Repeating strokes: {strokes_to_repeat}")
        
        self._processing = True
        try:
            for stroke_str in strokes_to_repeat:
                stroke = Stroke.from_steno(stroke_str)
                self.engine._machine_stroke_callback(stroke)
                self.log(f"Replayed stroke: {stroke_str}")
        except Exception as e:
            self.log(f"Error repeating strokes: {e}")
        finally:
            self._processing = False
        
    def repeat_from_mark(self):
        """Repeat all strokes from mark to current position"""
        if self.mark_position is None:
            self.log("No mark set, cannot repeat-to-mark")
            return
            
        # Get strokes from mark position to current
        history_list = list(self.stroke_history)
        if self.mark_position >= len(history_list):
            self.log(f"Mark position {self.mark_position} is beyond history length {len(history_list)}")
            return
            
        strokes_to_repeat = history_list[self.mark_position:]
        self.log(f"Repeating {len(strokes_to_repeat)} strokes from mark position {self.mark_position}")
        self.log(f"Strokes: {strokes_to_repeat}")
        
        self._processing = True
        try:
            for stroke_str in strokes_to_repeat:
                stroke = Stroke.from_steno(stroke_str)
                self.engine._machine_stroke_callback(stroke)
                self.log(f"Replayed stroke: {stroke_str}")
        except Exception as e:
            self.log(f"Error repeating from mark: {e}")
        finally:
            self._processing = False