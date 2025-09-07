import requests

def uni(url):
    try:
        res = requests.post(
            "https://freeseptemberapi.vercel.app/bypass",
            json={"url": url},
            timeout=10
        )
        res.raise_for_status()
        data = res.json()  # directly parse JSON
    except Exception as e:
        return f"Error: {e}"

    if "message" in data:
        return data["message"]  # return only the message string
    elif "url" in data:
        return data["url"]
    else:
        return f"Unexpected response: {data}"

print(uni("https://shor"))