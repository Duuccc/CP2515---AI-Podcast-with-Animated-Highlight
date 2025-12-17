# Create a test file: test_video_gen.py
import os
from app.services.video_generator import VideoGenerator

print("Before init:")
print(f"CWD: {os.getcwd()}")
print(f"videos exists: {os.path.exists('videos')}")

gen = VideoGenerator()

print("\nAfter init:")
print(f"videos exists: {os.path.exists('videos')}")
print(f"videos_dir: {gen.videos_dir}")
print(f"Absolute: {os.path.abspath(gen.videos_dir)}")

# List files
if os.path.exists('videos'):
    print(f"Videos directory created at: {os.path.abspath('videos')}")
else:
    print("ERROR: videos directory was NOT created!")