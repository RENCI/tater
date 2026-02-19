"""Basic Tater annotation application.

This is a minimal example showing how to create and run a Tater app.
"""
from tater import TaterApp


def main():
    """Run the basic annotation app."""
    # Create the app
    app = TaterApp(
        title="Basic Annotation App",
        theme="light"
    )
    
    # Run the server
    app.run(
        debug=True,
        port=8050
    )


if __name__ == "__main__":
    main()
