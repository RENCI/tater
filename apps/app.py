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
    
    # Load documents from the provided file
    if not app.load_documents(args.documents):
        return
    
    # Load schema if provided
    if args.schema:
        if not app.load_schema(args.schema):
            return
    
    # Run the server
    app.run(
        debug=args.debug,
        port=args.port,
        host=args.host
    )


if __name__ == "__main__":
    main()
