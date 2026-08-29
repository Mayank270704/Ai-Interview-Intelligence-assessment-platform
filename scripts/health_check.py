from urllib.request import urlopen


if __name__ == "__main__":
    with urlopen("http://localhost:8000/health", timeout=3) as response:
        print(response.read().decode())
