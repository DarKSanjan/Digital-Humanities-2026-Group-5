import requests
key = "sk_2cd275b3d7638e1c0c90f24725ebfeb68802de241c0f7378"
resp = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key})
voices = resp.json().get("voices", [])
print("All available voices:")
for v in voices:
    labels = v.get("labels", {})
    print(f"{v['voice_id']}: {v['name']} - {labels}")
