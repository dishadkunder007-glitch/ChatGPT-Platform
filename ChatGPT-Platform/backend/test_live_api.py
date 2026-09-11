import urllib.request
import json

def test():
    # 1. Get Guest Token
    req = urllib.request.Request('http://localhost:8000/api/auth/guest')
    with urllib.request.urlopen(req) as resp:
        guest_data = json.loads(resp.read().decode())
    token = guest_data['access_token']
    print('Guest login OK, user ID:', guest_data['user']['id'])

    # 2. Check Documents
    req = urllib.request.Request('http://localhost:8000/api/documents', headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as resp:
        docs = json.loads(resp.read().decode())
    print('Documents count:', len(docs))

    # 3. Create Conversation
    conv_payload = json.dumps({'title': 'Test Chat', 'model': 'qwen2.5:1.5b'}).encode('utf-8')
    req = urllib.request.Request('http://localhost:8000/api/conversations', data=conv_payload, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        conv = json.loads(resp.read().decode())
    conv_id = conv['id']
    print('Created test conversation:', conv_id)

    # 4. Send query 'hii' with use_rag=True
    chat_payload = json.dumps({
        'conversation_id': conv_id,
        'message': 'hii',
        'model': 'qwen2.5:1.5b',
        'use_rag': True
    }).encode('utf-8')

    req = urllib.request.Request('http://localhost:8000/api/chat/stream', data=chat_payload, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())

    full_res = result.get('full_content', '')
    print('Response for "hii":')
    print('-----------------------------------------')
    print(full_res)
    print('-----------------------------------------')
    print('Citations:', result.get('citations'))
    assert 'Digital Essentials' not in full_res, 'Old PDF was included!'
    assert 'Document Analysis' not in full_res, 'Document analysis header appeared on greeting!'
    assert len(result.get('citations', [])) == 0, 'Citations were returned for general greeting!'
    print('\nAPI LIVE TEST VERIFICATION PASSED!')

if __name__ == '__main__':
    test()
