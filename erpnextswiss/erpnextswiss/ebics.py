"""Compatibility entry points for the scheduled, fail-closed EBICS retrieval."""

from erpnextswiss.erpnextswiss.ebics_automation import sync, sync_connection


__all__ = ["sync", "sync_connection"]
