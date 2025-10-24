import subprocess

# Generate a short test tone to confirm ffmpeg works
cmd = [
    "ffmpeg",
    "-f", "lavfi",
    "-i", "sine=frequency=440:duration=3",
    "-q:a", "3",
    "test_tone.mp3",
    "-y"
]

print("Running ffmpeg test...")
result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)

if result.returncode == 0:
    print("✅ ffmpeg test successful — file 'test_tone.mp3' created.")
else:
    print("❌ ffmpeg test failed.")
