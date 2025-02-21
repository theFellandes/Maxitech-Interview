"""
Custom logger class to log messages with timestamps and session IDs.
"""
import datetime


class CustomLogger:
    """
    Custom logger class to log messages with timestamps and session IDs.
    """
    @staticmethod
    def log_message(session_id: str, node: str, message: str):
        print(f"[{datetime.datetime.now()}][Session: {session_id}][{node}] {message}")
