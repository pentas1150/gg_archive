"""
GG Archive - Desktop Application
Entry point for the application.
"""
import sys
from app import Application


def main():
    # Check for dev mode from command line args
    dev_mode = len(sys.argv) > 1 and sys.argv[1].lower() in ("dev", "development")

    # Qt 앱에 전달할 인수에서 dev 인수 제거
    qt_argv = [arg for arg in sys.argv if arg.lower() not in ("dev", "development")]

    app = Application(qt_argv, dev_mode=dev_mode)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
