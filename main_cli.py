import argparse
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Run the AI Assistant Backend server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)

if __name__ == "__main__":
    main()
