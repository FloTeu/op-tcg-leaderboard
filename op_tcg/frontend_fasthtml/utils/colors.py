from enum import Enum

class ChartColors(Enum):
    POSITIVE = '#22c55e'  # Green
    NEGATIVE = '#ef4444'  # Red
    NEUTRAL = '#60a5fa'   # Blue
    
    # Background colors (with transparency)
    TOOLTIP_BG = 'rgba(17, 24, 39, 0.9)'
    TOOLTIP_BORDER = '#374151'
    
    # Grid colors
    GRID = '#374151'
    TICK_TEXT = '#9ca3af'

    def __str__(self):
        return self.value 