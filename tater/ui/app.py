"""Core Tater Dash application."""
from typing import Optional
from dash import Dash, html, dcc
import dash_mantine_components as dmc


class TaterApp:
    """Main Tater annotation application.
    
    This class provides a Dash-based annotation interface that can be
    configured with schemas and documents either programmatically or
    via JSON/YAML configuration files.
    
    Example:
        >>> app = TaterApp(title="My Annotation Project")
        >>> app.run(debug=True, port=8050)
    """
    
    def __init__(
        self,
        title: str = "Tater Annotation Tool",
        theme: str = "light",
        external_stylesheets: Optional[list] = None,
    ):
        """Initialize the Tater application.
        
        Args:
            title: Application title shown in browser tab
            theme: UI theme ('light' or 'dark')
            external_stylesheets: Additional CSS stylesheets to include
        """
        self.title = title
        self.theme = theme
        
        # Initialize Dash app
        self.app = Dash(
            __name__,
            title=title,
            external_stylesheets=external_stylesheets or [],
            suppress_callback_exceptions=True
        )
        
        # Build layout
        self._setup_layout()
        
    def _setup_layout(self):
        """Set up the basic application layout."""
        self.app.layout = dmc.MantineProvider(
            theme={"colorScheme": self.theme},
            children=[
                dmc.Container([
                    dmc.Stack([
                        dmc.Center(
                            dmc.Title(
                                self.title,
                                order=1,
                                mt="xl"
                            )
                        ),
                        dmc.Paper(
                            dmc.Text(
                                "Tater annotation app initialized. Ready for configuration.",
                                ta="center"
                            ),
                            p="xl",
                            shadow="sm",
                            radius="md"
                        )
                    ], gap="lg")
                ], size="xl", mt="xl")
            ]
        )
    
    def run(
        self,
        debug: bool = False,
        port: int = 8050,
        host: str = "127.0.0.1",
        **kwargs
    ):
        """Run the Dash development server.
        
        Args:
            debug: Enable debug mode with hot reloading
            port: Port to run server on
            host: Host to bind to
            **kwargs: Additional arguments passed to app.run()
        """
        print(f"Starting Tater application...")
        print(f"  Title: {self.title}")
        print(f"  Theme: {self.theme}")
        print(f"  URL: http://{host}:{port}")
        print()
        
        self.app.run(
            debug=debug,
            port=port,
            host=host,
            **kwargs
        )
    
    def get_server(self):
        """Get the underlying Flask server.
        
        Useful for deployment with gunicorn or other WSGI servers.
        
        Returns:
            Flask server instance
        """
        return self.app.server
