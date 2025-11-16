# System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT BROWSER                          │
├─────────────────────────────────────────────────────────────────┤
│  /signup  │  /login  │  / (main app)                           │
│  QR Scan  │  TOTP    │  File Browser + Logout                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ├── HTTP Requests
                              │   (JWT in httponly cookie)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI APPLICATION                        │
├─────────────────────────────────────────────────────────────────┤
│  Authentication Routes:                                         │
│    • POST /api/signup      ──→  Generate TOTP + QR Code         │
│    • POST /api/login       ──→  Verify TOTP + Create JWT        │
│    • POST /api/verify-totp ──→  Verify & Create JWT             │
│    • POST /api/logout      ──→  Clear Cookie                    │
│                                                                  │
│  Protected Routes (with get_current_user):                      │
│    • GET /api/files        ──→  List files from user's blob     │
│    • POST /api/upload      ──→  Upload to user's blob           │
│    • GET /api/download/... ──→  Download from user's blob       │
│    • POST /api/upload-folder   ──→  Upload folder to user's blob│
│    • POST /api/download-folder ──→  Download folder from user's │
│    • GET /api/search       ──→  Search user's blob              │
│    • GET /api/me           ──→  Get current user info           │
└─────────────────────────────────────────────────────────────────┘
         │                                      │
         │                                      │
         ↓                                      ↓
┌─────────────────────┐              ┌──────────────────────────┐
│   MongoDB Database  │              │ Azure Blob Storage       │
├─────────────────────┤              ├──────────────────────────┤
│ Database:           │              │ User 1 → Container 1     │
│   blob-manager      │              │ User 2 → Container 2     │
│                     │              │ User 3 → Container 3     │
│ Collection:         │              │ ...                      │
│   users             │              │                          │
│                     │              │ Each user has own        │
│ Schema:             │              │ SAS URL stored in DB     │
│  - username (unique)│              │                          │
│  - totp_secret      │              │ Isolation enforced by    │
│  - blob_sas_url     │              │ using user's SAS URL     │
└─────────────────────┘              └──────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                      AUTHENTICATION FLOW                        │
└─────────────────────────────────────────────────────────────────┘

SIGNUP:
  User Input → Generate TOTP Secret → Create QR Code → Display QR
       ↓
  User Scans QR → Authenticator App Synced
       ↓
  Enter TOTP Code → Verify Code → Save to MongoDB → Create JWT
       ↓
  Set Cookie → Redirect to Main App

LOGIN:
  User Input (username + TOTP) → Get User from MongoDB
       ↓
  Verify TOTP Code → Create JWT → Set Cookie
       ↓
  Redirect to Main App

REQUEST AUTHORIZATION:
  Request with Cookie → Extract JWT → Verify JWT
       ↓
  Get User from MongoDB → Get User's blob_sas_url
       ↓
  Create Blob Client with User's SAS → Execute Operation
       ↓
  Return Response


┌─────────────────────────────────────────────────────────────────┐
│                       SECURITY LAYERS                           │
└─────────────────────────────────────────────────────────────────┘

Layer 1: TOTP 2FA
  ✓ Time-based codes (30s window)
  ✓ Secret stored in MongoDB
  ✓ QR code for easy setup

Layer 2: JWT Tokens
  ✓ 1-hour expiry
  ✓ Signed with SECRET_KEY
  ✓ Contains username claim

Layer 3: HttpOnly Cookies
  ✓ XSS protection (no JS access)
  ✓ Secure flag (HTTPS only)
  ✓ SameSite protection

Layer 4: User Isolation
  ✓ Separate blob SAS URL per user
  ✓ No cross-user access
  ✓ Database-level username uniqueness

Layer 5: Authorization Middleware
  ✓ Every protected route validates JWT
  ✓ User context loaded from DB
  ✓ Operations limited to user's storage


┌─────────────────────────────────────────────────────────────────┐
│                         FILE STRUCTURE                          │
└─────────────────────────────────────────────────────────────────┘

Blob-Manager/
│
├── app.py                    # Main FastAPI app + all routes
│
├── requirements.txt          # Python dependencies
│
├── .env                      # Environment variables (create this)
│
├── utils/
│   ├── __init__.py
│   ├── auth.py              # TOTP + JWT utilities
│   └── database.py          # MongoDB connection + operations
│
├── templates/
│   ├── index.html           # Main file browser (protected)
│   ├── login.html           # Login page with TOTP
│   └── signup.html          # Signup page with QR code
│
├── static/
│   └── cloud-storage.png    # Favicon
│
├── README.md                # Full documentation
├── SETUP.md                 # Quick setup guide
└── IMPLEMENTATION.md        # Implementation summary


┌─────────────────────────────────────────────────────────────────┐
│                      DATA FLOW EXAMPLE                          │
└─────────────────────────────────────────────────────────────────┘

Example: User Uploads a File

1. User clicks "Upload Files" in browser
2. Browser sends POST /api/upload with JWT cookie
3. FastAPI receives request
4. get_current_user() dependency:
   - Extracts JWT from cookie
   - Verifies JWT signature and expiry
   - Extracts username from JWT
5. Queries MongoDB for user document
6. Retrieves user's blob_sas_url
7. Creates Azure BlobServiceClient with user's SAS URL
8. Gets container_client from user's storage
9. Uploads file to user's blob container
10. Returns success response
11. Browser displays success toast
12. File list refreshes showing new file

At NO point can User A access User B's files because:
  - Each request uses the authenticated user's SAS URL
  - SAS URL is unique to each user's blob storage
  - Azure enforces storage isolation at the container level
```
