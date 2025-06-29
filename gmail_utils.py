import os
import base64
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

def authenticate_gmail():
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("misc/token.json"):
        creds = Credentials.from_authorized_user_file("misc/token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "misc/hn-creds-dt.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("misc/hn-creds-dt.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def get_messages_by_label(service, labelid):
    response = service.users().messages().list(userId='me', labelIds=[labelid]).execute()
    messages = []
    if 'messages' in response:
        messages.extend(response['messages'])
    return messages

def get_message_details(service, msg_id, format='full'):
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format=format).execute()
        return message
    except Exception as error:
        print(f'An error occurred: {error}')
        return None

def get_content_id(part):
    """Get Content-ID from headers for inline image reference."""
    headers = part.get('headers', [])
    for header in headers:
        if header['name'].lower() == 'content-id':
            # Strip < and > if present
            cid = header['value']
            if cid.startswith('<') and cid.endswith('>'):
                cid = cid[1:-1]
            return cid
    return None


def is_image(filename):
    """Check if a filename is likely an image based on extension."""
    if not filename:
        return False
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    return any(filename.lower().endswith(ext) for ext in image_extensions)

def process_parts(service, user_id, msg_id, parts):
    """Process message parts to extract text, HTML, and images."""
    plain_text = ""
    html_content = ""
    images = []

    print('PROCESS PARTS!!')
    
    for part in parts:
        mime_type = part.get('mimeType', '')

        # Handle nested parts recursively
        if 'parts' in part:
            nested_text, nested_html, nested_images = process_parts(service, user_id, msg_id, part['parts'])
            plain_text += nested_text
            html_content += nested_html
            images.extend(nested_images)
            continue
        
        # Get part body
        body = part.get('body', {})
        
        # Extract content based on MIME type
        if 'data' in body:
            data = base64.urlsafe_b64decode(body['data']).decode('utf-8', errors='replace')
            if 'text/plain' in mime_type:
                plain_text += data
            elif 'text/html' in mime_type:
                html_content += data
        
        # Handle attachments (images)
        if 'attachmentId' in body:
            filename = part.get('filename', '')
            if is_image(filename) or 'image/' in mime_type:
                # Get attachment data
                attachment = service.users().messages().attachments().get(
                    userId=user_id, messageId=msg_id, id=body['attachmentId']).execute()
                
                # Decode attachment data
                file_data = base64.urlsafe_b64decode(attachment['data'])
                
                # Add to images list
                images.append({
                    'filename': filename,
                    'content_id': get_content_id(part),
                    'data': file_data,
                    'mime_type': mime_type
                })
    
    return plain_text, html_content, images

def get_message_content(service, msg_id, user_id='me'):
    """Get the content of a message including text, HTML, and images."""
    try:
        # Get the full message
        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
        
        payload = message['payload'] ## ['partId', 'mimeType', 'filename', 'headers', 'body']
        headers = payload.get('headers', [])
        
        # Get subject and sender
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'No Date')
        # received = next((h['value'] for h in headers if h['name'].lower() == 'received'), 'No Date')
        
        ### can get received from here
        
        # Initialize variables to hold content
        plain_text = ""
        html_content = ""
        images = []
        
        # breakpoint()
        
        # Extract partsn
        if 'parts' in payload:
            print('parts')
            plain_text, html_content, images = process_parts(service, user_id, msg_id, payload['parts'])
        else:
            print('single')
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                content = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                mime_type = payload.get('mimeType', '')
                if 'text/plain' in mime_type:
                    plain_text = content
                elif 'text/html' in mime_type:
                    html_content = content
        
        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'plain_text': plain_text,
            'html_content': html_content,
            'images': images,
            'date':date
        }
        
    except Exception as error:
        print(f'Error getting message content: {error}')
        return None
