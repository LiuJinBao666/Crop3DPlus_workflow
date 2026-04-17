def run() -> int:
    try:
        from crop3dplus_gui_app.main import main
    except ModuleNotFoundError as exc:
        missing = exc.name or "dependency"
        if missing in {"PySide6", "PySide2"}:
            print("Missing Qt dependency: install PySide6 or PySide2 first.")
        else:
            print(f"Missing dependency: {missing}")
        print("Install the required packages before launching the GUI:")
        print("  pip install PySide6 torch torchvision transformers pillow")
        return 1

    main()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
