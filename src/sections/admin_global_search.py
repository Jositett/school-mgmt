"""
Global search functionality for admin view.

This module provides the global search handler that can be used across admin sections.
"""

# Global search handler class
class AdminGlobalSearch:
    """Handles global search functionality for admin view sections."""

    def __init__(self, page, initial_query=""):
        """Initialize the global search handler.

        Args:
            page: The Flet page instance
            initial_query: Initial search query (default: "")
        """
        self.page = page
        self.global_search_query = initial_query

    def on_global_search_change(self, e):
        """Handle global search changes."""
        self.global_search_query = e.control.value or ""
        # Update all sections (they will use the global search as fallback)
        # Each section checks for its own search first, then global
        self.page.update()

    def get_search_query(self):
        """Get the current global search query."""
        return self.global_search_query

    def set_search_query(self, query):
        """Set the global search query programmatically."""
        self.global_search_query = query or ""

    def create_search_field(self, **kwargs):
        """Create a global search field.

        Returns:
            ft.TextField: Configured search field
        """
        import flet as ft

        return ft.TextField(
            label="Search across all sections",
            hint_text="Search batches, classes, users, or face data",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=self.on_global_search_change,
            **kwargs
        )


# Standalone function version for backward compatibility
def create_global_search_handler(page, initial_query=""):
    """Create a global search handler instance.

    Args:
        page: The Flet page instance
        initial_query: Initial search query (default: "")

    Returns:
        AdminGlobalSearch: Configured search handler
    """
    return AdminGlobalSearch(page, initial_query)