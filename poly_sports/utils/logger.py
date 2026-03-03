"""Logger module with optional pretty-fancy Node.js bridge."""
import atexit
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

LogLevel = Literal['trace', 'debug', 'info', 'warn', 'error', 'fatal']


class PrettyFancyBridge:
    """Bridge Python log lines to a Node pretty-fancy logger process."""

    def __init__(self) -> None:
        self.enabled = os.getenv("USE_PRETTY_FANCY_LOGGER", "false").lower() == "true"
        self.node_bin = os.getenv("PRETTY_FANCY_NODE_BIN", "node")
        root = Path(__file__).resolve().parents[2]
        default_script = root / "node_logger" / "pretty_fancy_bridge.mjs"
        self.script_path = Path(os.getenv("PRETTY_FANCY_BRIDGE_PATH", str(default_script)))
        self.proc: Optional[subprocess.Popen[str]] = None
        if self.enabled:
            atexit.register(self.close)

    def _start_if_needed(self) -> bool:
        if not self.enabled:
            return False
        if self.proc and self.proc.poll() is None:
            return True
        if not self.script_path.exists():
            self.enabled = False
            return False
        try:
            self.proc = subprocess.Popen(
                [self.node_bin, str(self.script_path)],
                stdin=subprocess.PIPE,
                stdout=None,
                stderr=None,
                text=True,
                bufsize=1,
            )
            return self.proc.stdin is not None
        except Exception:
            self.enabled = False
            self.proc = None
            return False

    def emit(self, level: LogLevel, message: str) -> bool:
        """Emit a message to pretty-fancy; return False on fallback."""
        if not self._start_if_needed() or not self.proc or not self.proc.stdin:
            return False
        payload = {"level": level, "message": message}
        try:
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()
            return True
        except Exception:
            self.close()
            return False

    def close(self) -> None:
        """Close bridge process if running."""
        if not self.proc:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            if self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass
        finally:
            self.proc = None


class Logger:
    """Colorful logger with optional pretty-fancy output backend."""

    def __init__(self):
        self.colors = {
            'reset': '\033[0m',
            'trace': '\033[90m',
            'debug': '\033[36m',
            'info': '\033[32m',
            'warn': '\033[33m',
            'error': '\033[31m',
            'fatal': '\033[35m',
        }
        
        self.level_icons = {
            'trace': '🔍',
            'debug': '🐛',
            'info': 'ℹ️',
            'warn': '⚠️',
            'error': '❌',
            'fatal': '💀',
        }
        self.pretty_bridge = PrettyFancyBridge()
    
    def format_timestamp(self) -> str:
        """Format current timestamp as ISO 8601"""
        return datetime.now().isoformat()
    
    def format_message(
        self, 
        level: LogLevel, 
        message: str, 
        timestamp: bool = True, 
        colorize: bool = True
    ) -> str:
        """Format a log message with timestamp, icon, and color"""
        color = self.colors[level] if colorize else ''
        reset = self.colors['reset'] if colorize else ''
        icon = self.level_icons[level]
        time_str = f"[{self.format_timestamp()}]" if timestamp else ''
        level_str = level.upper().ljust(5)
        
        return f"{color}{time_str} {icon} {level_str}{reset} {message}"
    
    def _compose_message(self, message: str, *args) -> str:
        if not args:
            return message
        suffix = " ".join(str(arg) for arg in args)
        return f"{message} {suffix}"

    def _emit(self, level: LogLevel, message: str, *args) -> None:
        text = self._compose_message(message, *args)
        if self.pretty_bridge.emit(level, text):
            return
        formatted = self.format_message(level, text)
        stream = sys.stderr if level in {"warn", "error", "fatal"} else sys.stdout
        print(formatted, file=stream)

    def trace(self, message: str, *args) -> None:
        """Log a trace message"""
        self._emit('trace', message, *args)
    
    def debug(self, message: str, *args) -> None:
        """Log a debug message"""
        self._emit('debug', message, *args)
    
    def info(self, message: str, *args) -> None:
        """Log an info message"""
        self._emit('info', message, *args)
    
    def warn(self, message: str, *args) -> None:
        """Log a warning message"""
        self._emit('warn', message, *args)
    
    def error(self, message: str, *args) -> None:
        """Log an error message"""
        self._emit('error', message, *args)
    
    def fatal(self, message: str, *args) -> None:
        """Log a fatal message"""
        self._emit('fatal', message, *args)
    
    def log(self, level: LogLevel, message: str, *args) -> None:
        """Generic log method that accepts a log level"""
        method_map = {
            'trace': self.trace,
            'debug': self.debug,
            'info': self.info,
            'warn': self.warn,
            'error': self.error,
            'fatal': self.fatal,
        }
        method = method_map.get(level)
        if method:
            method(message, *args)


# Initialize logger instance
logger = Logger()

