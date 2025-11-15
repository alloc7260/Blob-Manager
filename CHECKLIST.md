# Pre-Launch Checklist

## ✅ Installation Checklist

- [ ] Python 3.8+ installed
- [ ] MongoDB installed and running (or MongoDB Atlas connection ready)
- [ ] Azure Blob Storage account created
- [ ] Azure container created with SAS URL generated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file created with MONGO_URI and JWT_SECRET_KEY
- [ ] Authenticator app installed on mobile device

## ✅ Configuration Checklist

- [ ] `.env` file exists in project root
- [ ] `MONGO_URI` is set correctly
- [ ] `JWT_SECRET_KEY` is set to a secure random value
- [ ] MongoDB is accessible from the application
- [ ] Azure Blob SAS URL has read/write/list permissions
- [ ] SAS URL expiry date is in the future

## ✅ Testing Checklist

### Basic Functionality
- [ ] Application starts without errors: `python app.py`
- [ ] Can access http://localhost:8000
- [ ] Redirects to /login when not authenticated
- [ ] /signup page loads correctly
- [ ] /login page loads correctly

### Signup Flow
- [ ] Can enter username on signup page
- [ ] Can enter Azure Blob SAS URL
- [ ] QR code generates and displays
- [ ] Can scan QR code with authenticator app
- [ ] Authenticator app shows 6-digit code
- [ ] Can verify TOTP code successfully
- [ ] Redirects to main app after verification
- [ ] JWT cookie is set
- [ ] Username appears in navigation bar

### Login Flow
- [ ] Can enter username on login page
- [ ] Can enter TOTP code from authenticator
- [ ] Login succeeds with valid credentials
- [ ] Login fails with invalid TOTP code
- [ ] Login fails with non-existent username
- [ ] Redirects to main app after successful login

### File Operations
- [ ] Can view file browser after login
- [ ] Can upload a file
- [ ] Uploaded file appears in list
- [ ] Can download uploaded file
- [ ] Can upload a folder
- [ ] Folder structure is preserved
- [ ] Can search for files
- [ ] Can download folder as ZIP

### Security Features
- [ ] Cannot access /api/files without authentication
- [ ] Cannot access /api/upload without authentication
- [ ] JWT token expires after 1 hour (test by waiting)
- [ ] Expired token redirects to login
- [ ] Logout button works
- [ ] Logout clears cookie and redirects to login
- [ ] Username uniqueness is enforced
- [ ] Duplicate username signup fails

### Multi-User Testing (Optional)
- [ ] Create second user with different SAS URL
- [ ] Login with user 1, upload files
- [ ] Logout, login with user 2
- [ ] User 2 cannot see user 1's files
- [ ] User 2 can upload their own files
- [ ] Files are stored in correct blob containers

## ✅ Security Checklist

- [ ] JWT_SECRET_KEY is strong and random (not default)
- [ ] MongoDB has authentication enabled (production)
- [ ] HTTPS is enabled (production)
- [ ] SAS URLs have minimum required permissions
- [ ] SAS URLs have reasonable expiry dates
- [ ] Cookies have secure flag set (production)
- [ ] TOTP secret is never exposed to client
- [ ] User data is isolated in database

## ✅ Documentation Checklist

- [ ] README.md reviewed
- [ ] SETUP.md reviewed
- [ ] IMPLEMENTATION.md reviewed
- [ ] ARCHITECTURE.md reviewed
- [ ] All team members understand the system

## ✅ Deployment Checklist (Production)

- [ ] All environment variables set in production
- [ ] MongoDB connection string for production ready
- [ ] MongoDB authentication enabled
- [ ] HTTPS certificate installed
- [ ] Secure cookies enabled (secure=True works)
- [ ] Rate limiting implemented (optional but recommended)
- [ ] Logging configured
- [ ] Error monitoring setup
- [ ] Backup strategy for MongoDB
- [ ] SAS token rotation plan
- [ ] Health check endpoint added (optional)

## ✅ Known Limitations

- Users must manage their own Azure Blob Storage
- One SAS URL per user (no multiple storage support)
- No password recovery mechanism (TOTP only)
- No email verification
- No admin interface
- No file sharing between users
- No file versioning

## ✅ Troubleshooting Quick Reference

### "pymongo.errors.ServerSelectionTimeoutError"
→ MongoDB is not running or MONGO_URI is incorrect

### "Invalid TOTP code"
→ Device time not synchronized or wrong code entered

### "Username already exists"
→ Username must be unique, try different username

### "Not authenticated" or redirect to login
→ JWT token expired or invalid, login again

### "azure.core.exceptions.HttpResponseError"
→ SAS URL invalid, expired, or missing permissions

### QR code not displaying
→ Check browser console for errors, ensure signup request succeeded

### Cookie not being set
→ Check browser security settings, ensure localhost or HTTPS

## 🎉 Ready to Launch

Once all items are checked, your TOTP authentication system is ready!

### Quick Start Command:
```bash
# Start MongoDB (if local)
# Windows: net start MongoDB
# Linux/Mac: sudo systemctl start mongod

# Start the application
python app.py

# or with uvicorn
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### First User Setup:
1. Open http://localhost:8000
2. Click "Sign up"
3. Enter username
4. Paste Azure Blob SAS URL
5. Scan QR code with authenticator app
6. Enter verification code
7. Start using the app!

---

**Need Help?**
- Check SETUP.md for detailed setup instructions
- Check ARCHITECTURE.md for system design
- Check IMPLEMENTATION.md for what was built
- Check README.md for comprehensive documentation
