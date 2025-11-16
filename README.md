# Blob Manager - Secure Cloud Storage with TOTP Authentication

A FastAPI-based web application for managing Azure Blob Storage with secure TOTP (Time-based One-Time Password) authentication.

## Features

- 🔐 **TOTP-based Authentication** - Secure 2FA login using authenticator apps
- 👤 **User Management** - Each user has their own isolated blob storage
- 📁 **File Management** - Upload, download, search files and folders
- 🔒 **JWT Sessions** - Secure 1-hour session tokens stored in httponly cookies
- 🗄️ **MongoDB Integration** - User data and credentials stored securely
- ☁️ **Azure Blob Storage** - Each user connects to their own blob container

## Prerequisites

- Python 3.8+
- MongoDB (local or Atlas)
- Azure Blob Storage account with SAS URL
- Authenticator app (Google Authenticator, Authy, etc.)

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/alloc7260/Blob-Manager.git
   cd Blob-Manager
   ```
2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment variables**

   Create a `.env` file in the root directory:

   ```env
   MONGO_URI=mongodb://localhost:27017/
   JWT_SECRET_KEY=your-secret-key-change-this-in-production
   ```
4. **Set up MongoDB**

   - Install MongoDB locally or use MongoDB Atlas
   - Update `MONGO_URI` in `.env` with your connection string
   - Database name: `blob-manager`
   - Collection: `users` (created automatically)

## Usage

1. **Start the application**

   ```bash
   python app.py
   ```

   Or with uvicorn:

   ```bash
   uvicorn app:app --reload
   ```
2. **Access the application**

   - Open browser to `http://localhost:8000`
   - You'll be redirected to the login page
3. **Sign up for a new account**

   - Navigate to `/signup`
   - Enter a unique username
   - Paste your Azure Blob Storage SAS URL
   - Scan the QR code with your authenticator app
   - Enter the 6-digit code to verify and login
4. **Login**

   - Navigate to `/login`
   - Enter your username
   - Enter the current TOTP code from your authenticator app

## Authentication Flow

### Signup Process

1. User enters username and Azure Blob SAS URL
2. System generates TOTP secret and QR code
3. User scans QR code with authenticator app
4. User enters TOTP code to verify setup
5. JWT token is issued and stored in httponly cookie

### Login Process

1. User enters username
2. User enters current TOTP code from authenticator app
3. System verifies TOTP code
4. JWT token is issued (1-hour expiry)
5. Token stored in httponly secure cookie

## Security Features

- ✅ TOTP-based 2FA authentication
- ✅ JWT tokens with 1-hour expiry
- ✅ HttpOnly secure cookies prevent XSS attacks
- ✅ User isolation - each user can only access their own blob storage
- ✅ MongoDB stores user credentials securely
- ✅ SAS URL per user for Azure Blob Storage access

## API Endpoints

### Authentication

- `GET /login` - Login page
- `GET /signup` - Signup page
- `POST /api/signup` - Create new user account
- `POST /api/login` - Login with username and TOTP
- `POST /api/verify-totp` - Verify TOTP code
- `POST /api/logout` - Logout and clear session
- `GET /api/me` - Get current user info

### File Management (Authenticated)

- `GET /` - Main file browser interface
- `GET /api/files` - List all files and folders
- `POST /api/upload` - Upload a file
- `POST /api/upload-folder` - Upload entire folder
- `GET /api/download/{path}` - Download a file
- `POST /api/download-folder` - Download folder as ZIP
- `GET /api/search` - Search files by name

## Project Structure

```
Blob-Manager/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── utils/
│   ├── auth.py           # TOTP and JWT authentication utilities
│   └── database.py       # MongoDB connection and user management
├── templates/
│   ├── index.html        # Main file browser interface
│   ├── login.html        # Login page
│   └── signup.html       # Signup page with QR code
└── static/
    └── cloud-storage.png # Favicon
```

## MongoDB Schema

### Users Collection

```json
{
  "_id": "ObjectId",
  "username": "string (unique)",
  "totp_secret": "string (base32 encoded)",
  "blob_sas_url": "string (Azure Blob SAS URL)"
}
```

## Environment Variables

| Variable           | Description                | Example                        |
| ------------------ | -------------------------- | ------------------------------ |
| `MONGO_URI`      | MongoDB connection string  | `mongodb://localhost:27017/` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | `your-secret-key-here`       |

## Technologies Used

- **Backend**: FastAPI, Python
- **Authentication**: PyOTP (TOTP), python-jose (JWT)
- **Database**: MongoDB (pymongo)
- **Storage**: Azure Blob Storage
- **Frontend**: HTML, Tailwind CSS, Axios

## Notes

- Each user must provide their own Azure Blob Storage SAS URL
- SAS URLs should have read/write/list permissions
- JWT tokens expire after 1 hour (configurable in `utils/auth.py`)
- TOTP codes have a 30-second validity window
- Username must be unique across all users

## Security Recommendations

1. Use a strong, random `JWT_SECRET_KEY` in production
2. Use HTTPS in production for secure cookie transmission
3. Regularly rotate SAS tokens
4. Set appropriate SAS token permissions (minimum required)
5. Use MongoDB authentication in production
6. Consider rate limiting for authentication endpoints

## Troubleshooting

- **"Not authenticated" error**: Check if JWT token is valid and not expired
- **"Invalid TOTP code"**: Ensure your device time is synchronized
- **MongoDB connection issues**: Verify `MONGO_URI` is correct
- **Blob storage errors**: Check if SAS URL is valid and has proper permissions

## License

MIT License
