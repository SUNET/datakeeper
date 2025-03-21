import os
import time
import uuid


def create_files():
    current_dir = os.path.dirname(__file__)
    directory = os.path.join(current_dir, "data", "csv")
    # parent_dir = os.path.dirname(current_dir)
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)
    for _ in range(3):
        full_path = os.path.join(directory, f"data-{uuid.uuid4()}.csv")
        try:
            with open(file=full_path, mode="w") as file:
                file.write("x, y, labels\n")
                file.write("44, 60, paris\n")
                file.write("56, 88, london\n")
                file.write("94, 24, lisbon\n")
        except (PermissionError, OSError) as e:
            print(f"Failed to create file {full_path}: {str(e)}")


def main():
    while True:
        print("creating files...")
        create_files()
        print("Done!")
        print("sleeping...")
        time.sleep(60)


if __name__ == "__main__":
    main()

