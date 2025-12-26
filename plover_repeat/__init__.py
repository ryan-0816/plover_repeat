import os
from collections import deque
from plover.engine import StenoEngine
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke

class PloverRepeat:
    fname = os.path.join(CONFIG_DIR, 'repeat_strokes.txt')
    MAX_HISTORY = 100
    
    # Binary repeat mappings (right hand: -FPLTD)
    REPEAT_STROKES = {
        'RA*PT': 1, 'RO*PT': 2, 'RAO*PT': 3, 'R*EPT': 4, 'RA*EPT': 5,
        'RO*EPT': 6, 'RAO*EPT': 7, 'R*UPT': 8, 'RA*UPT': 9, 'RO*UPT': 10,
        'RAO*UPT': 11, 'R*EUPT': 12, 'RA*EUPT': 13, 'RO*EUPT': 14, 'RAO*EUPT': 15,
    }
    
    MARK_STROKE = '#-FT'      # Mark current position
    REPEAT_TO_STROKE = '#-FD'  # Repeat from mark to current
    
    def __init__(self, engine: StenoEngine) -> None:
        self.engine = engine
        self.stroke_history = deque(maxlen=self.MAX_HISTORY)
        self.mark_position = None
        self._processing = False
        
    def start(self) -> None:
        self.engine.hook_connect('stroked', self.on_stroked)
        self.load_history()
        
    def stop(self) -> None:
        self.engine.hook_disconnect('stroked', self.on_stroked)
        self.save_history()
        
    def load_history(self):
        """Load stroke history from file"""
        pass
        
    def save_history(self):
        """Save stroke history to file"""
        pass
        
    def on_stroked(self, stroke: Stroke):
        if self._processing:
            return
            
        stroke_str = stroke.rtfcre
        
        # Check for repeat commands
        if stroke_str in self.REPEAT_STROKES:
            n = self.REPEAT_STROKES[stroke_str]
            self.repeat_last_n(n)
            return
            
        # Check for mark
        if stroke_str == self.MARK_STROKE:
            self.mark_position = len(self.stroke_history)
            return
            
        # Check for repeat-to-mark
        if stroke_str == self.REPEAT_TO_STROKE:
            self.repeat_from_mark()
            return
            
        # Record stroke in history (if not a repeat command)
        self.stroke_history.append(stroke_str)
        
    def repeat_last_n(self, n):
        """Repeat the last n strokes"""
        pass
        
    def repeat_from_mark(self):
        """Repeat all strokes from mark to current position"""
        pass