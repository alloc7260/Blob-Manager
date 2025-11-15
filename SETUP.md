# Quick Setup Guide

## Step-by-Step Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup MongoDB

**Option A: Local MongoDB**
- Install MongoDB Community Edition
- Start MongoDB service:
  ```bash
  # Windows
  net start MongoDB
  
  # Linux/Mac
  sudo systemctl start mongod
  ```

**Option B: MongoDB Atlas (Cloud)**
- Create free account at https://www.mongodb.com/cloud/atlas
- Create a cluster
- Get connection string (replace <password> with your password)
- Example: `mongodb+srv://username:<password>@cluster.mongodb.net/`

### 3. Configure Environment Variables

Create `.env` file:
```env
MONGO_URI=mongodb://localhost:27017/
JWT_SECRET_KEY=your-secret-key-change-this-in-production
```

**Generate a secure JWT secret:**
```python
# Run this in Python to generate a random secret
import secrets
print(secrets.token_urlsafe(32))
```

### 4. Get Azure Blob Storage SAS URL

1. Go to Azure Portal
2. Navigate to your Storage Account
3. Go to your container
4. Click "Shared access signature"
5. Set permissions: Read, Write, List, Create
6. Set expiry date (e.g., 1 year from now)
7. Click "Generate SAS token and URL"
8. Copy the "Blob SAS URL"

Example SAS URL format:
```
https://youraccount.blob.core.windows.net/containername?sp=racwl&st=...
```

### 5. Run the Application

```bash
# Method 1: Direct Python
python app.py

# Method 2: Using uvicorn (recommended for development)
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 6. Create Your First Account

1. Open browser to http://localhost:8000
2. Click "Sign up"
3. Enter username (e.g., "john_doe")
4. Paste your Azure Blob SAS URL
5. Click "Continue"
6. Scan QR code with authenticator app:
   - Google Authenticator (iOS/Android)
   - Microsoft Authenticator (iOS/Android)
   - Authy (iOS/Android/Desktop)
7. Enter 6-digit code from app
8. Click "Verify & Sign In"

### 7. Test the System

1. You should be logged in and see the file browser
2. Try uploading a file
3. Try creating folders
4. Logout and login again with TOTP code

## Troubleshooting

### MongoDB Connection Error
```
pymongo.errors.ServerSelectionTimeoutError
```
**Solution**: Check if MongoDB is running and MONGO_URI is correct

### Invalid TOTP Code
```
"Invalid TOTP code"
```
**Solution**: 
- Ensure device time is synchronized
- Check if you're using the latest code (refreshes every 30 seconds)
- Verify you scanned the correct QR code

### Blob Storage Access Error
```
azure.core.exceptions.HttpResponseError
```
**Solution**: 
- Check if SAS URL is valid and not expired
- Verify SAS URL has read/write/list permissions
- Ensure container exists in Azure

### JWT Token Expired
```
"Invalid token" or redirect to login
```
**Solution**: 
- Login again (tokens expire after 1 hour)
- This is normal security behavior

## Testing with Multiple Users

1. Each user needs their own Azure Blob container/SAS URL
2. Users are completely isolated - can't see each other's files
3. To test multi-user:
   - Create multiple containers in Azure
   - Generate SAS URL for each
   - Sign up with different usernames
   - Each user will only see their own files

## Production Deployment Checklist

- [ ] Change JWT_SECRET_KEY to a strong random value
- [ ] Use MongoDB with authentication enabled
- [ ] Use HTTPS (not HTTP)
- [ ] Set secure cookie flags correctly
- [ ] Use environment-specific .env files
- [ ] Implement rate limiting on auth endpoints
- [ ] Set up monitoring and logging
- [ ] Regular SAS token rotation
- [ ] Backup MongoDB regularly
- [ ] Use Azure Key Vault for secrets (optional)

## Development Tips

**Auto-reload on code changes:**
```bash
uvicorn app:app --reload
```

**View MongoDB data:**
```bash
# Using mongosh
mongosh
use blob-manager
db.users.find().pretty()
```

**Clear all users (reset):**
```bash
mongosh
use blob-manager
db.users.deleteMany({})
```

**Test TOTP locally:**
```python
import pyotp
secret = "YOUR_SECRET_HERE"
totp = pyotp.TOTP(secret)
print(totp.now())  # Current valid code
```

## Next Steps

After setup, you can:
- Customize the UI in templates/
- Add more features (sharing, permissions, etc.)
- Implement file preview
- Add file versioning
- Set up automated backups
- Deploy to cloud (Azure App Service, AWS, etc.)
