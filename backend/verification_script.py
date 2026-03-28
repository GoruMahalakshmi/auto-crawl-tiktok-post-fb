import sys
import os

# Add manual path to backend app
sys.path.append(r'c:\Users\Beemo\Downloads\social_tool\backend')

from app.services.fb_graph import upload_video_to_facebook
from app.services.ai_generator import generate_caption

def test_fb_payload():
    print("Testing Facebook Payload...")
    # Mock requests.post
    import requests
    from unittest.mock import MagicMock
    
    requests.post = MagicMock()
    
    # Create a dummy file
    dummy_file = 'dummy.mp4'
    with open(dummy_file, 'w') as f:
        f.write('dummy content')
    
    try:
        upload_video_to_facebook(dummy_file, "Test Caption", "page_123", "token_123")
        
        args, kwargs = requests.post.call_args
        data = kwargs.get('data', {})
        print(f"Payload Data: {data}")
        assert data.get('published') == 'true'
        assert data.get('description') == 'Test Caption'
        print("Facebook Payload Test Passed!")
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

def test_ai_model_name():
    print("Testing AI Model Name...")
    # Check if the code uses the correct model name in its strings
    import inspect
    source = inspect.getsource(generate_caption)
    print(f"Found model name in source: {'gemini-1.5-flash' in source}")
    assert 'gemini-1.5-flash' in source
    assert 'gemini-2.5-flash' not in source
    print("AI Model Name Test Passed!")

if __name__ == "__main__":
    try:
        test_fb_payload()
        test_ai_model_name()
    except Exception as e:
        print(f"Verification Failed: {e}")
        sys.exit(1)
