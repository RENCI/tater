"""Basic Tater annotation application.

This is a minimal example showing how to create and run a Tater app.
"""
from tater import TaterApp, parse_args


def main():
    """Run the basic annotation app."""
    args = parse_args()
    
    # Create the app
    app = TaterApp(
        title="Basic Annotation App",
        theme="light"
    )
    
    # Run the server
    app.run(
        debug=args.debug,
        port=args.port,
        host=args.host
    )


if __name__ == "__main__":
    main()
