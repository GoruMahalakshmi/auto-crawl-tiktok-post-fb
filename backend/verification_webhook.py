import sys
import os

# Add manual path to backend app
sys.path.append(r'c:\Users\Beemo\Downloads\social_tool\backend')

from app.services.fb_graph import upload_video_to_facebook
from unittest.mock import MagicMock
import requests

def test_webhook_upload():
    print("Testing Webhook Upload Logic...")
    requests.post = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'id': 'success_123'}
    requests.post.return_value = mock_response

    dummy_file = 'dummy_webhook.mp4'
    with open(dummy_file, 'w') as f:
        f.write('dummy content')
    
    try:
        res = upload_video_to_facebook(dummy_file, "Test Caption", "page_123", "https://hook.us1.make.com/abc123xyz")
        
        args, kwargs = requests.post.call_args
        url = args[0]
        data = kwargs.get('data', {})
        
        assert url == "https://hook.us1.make.com/abc123xyz"
        assert data.get('caption') == 'Test Caption'
        assert data.get('page_id') == 'page_123'
        assert 'file' in kwargs.get('files', {})
        assert res.get('id') == 'success_123'
        
        print("Webhook Upload Test Passed!")
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

if __name__ == "__main__":
    try:
        test_webhook_upload()
    except Exception as e:
        print(f"Verification Failed: {e}")
        sys.exit(1)
