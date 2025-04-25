import requests
import time
import json

def test_endpoints():
    base_url = 'http://localhost:8005'
    
    # 1. Test health endpoint
    print("\n1. Testing /health endpoint...")
    try:
        health_response = requests.get(f'{base_url}/health')
        print(f"Status Code: {health_response.status_code}")
        print("Response:", health_response.json())
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server. Is the backend running?")
        return
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return

    # 2. Test create-podcast endpoint
    print("\n2. Testing /create-podcast endpoint...")
    try:
        files = {
            'pdf_file': ('sarvamangala2018_book_chapter.pdf', open('sarvamangala2018_book_chapter.pdf', 'rb'), 'application/pdf'),
        }
        data = {
            'model': 'deepseek-r1-distill-llama-70b',
            'sync': 'true'
        }
        create_response = requests.post(f'{base_url}/create-podcast', files=files, data=data)
        print(f"Status Code: {create_response.status_code}")
        print("Response:", create_response.json())
        
        if create_response.status_code == 200:
            task_id = create_response.json().get('task_id')
            
            # 3. Test status endpoint
            print("\n3. Testing /podcast/{task_id}/status endpoint...")
            for _ in range(3):  # Check status 3 times
                status_response = requests.get(f'{base_url}/podcast/{task_id}/status')
                print(f"Status Code: {status_response.status_code}")
                print("Response:", status_response.json())
                time.sleep(2)  # Wait 2 seconds between status checks
            
            # 4. Test podcast download endpoint
            print("\n4. Testing /podcast/{task_id} endpoint...")
            download_response = requests.get(f'{base_url}/podcast/{task_id}')
            print(f"Status Code: {download_response.status_code}")
            if download_response.status_code == 200:
                print("Successfully got podcast audio response")
            else:
                print("Response:", download_response.json())
    except FileNotFoundError:
        print("ERROR: sarvamangala2018_book_chapter.pdf not found. Please create the PDF file first.")
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    test_endpoints()
