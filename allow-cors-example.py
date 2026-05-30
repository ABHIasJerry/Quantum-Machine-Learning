from fastapi.middleware.cors import CORSMiddleware

# =====================================================================
# OPTION 1: Single domain (most common production setup)
# =====================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# =====================================================================
# OPTION 2: Multiple explicit domains
# (e.g. separate frontend, admin portal, and partner site)
# =====================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://myapp.com",
        "https://admin.myapp.com",
        "https://partner.externalsite.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# =====================================================================
# OPTION 3: Environment-driven (recommended pattern)
# Load allowed origins from an env var so no code change is needed
# across dev / staging / prod deployments.
#
# Set in your environment:
#   ALLOWED_ORIGINS="https://myapp.com,https://admin.myapp.com"
# =====================================================================
import os

ALLOWED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# =====================================================================
# OPTION 4: Subdomain wildcard via regex
# Allows any subdomain of myapp.com without listing each one.
# Useful for: feature branches, tenant subdomains, microservices.
#
# Matches: app.myapp.com, admin.myapp.com, tenant-x.myapp.com
# Does NOT match: myapp.com (add explicitly if needed)
# =====================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.myapp\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# =====================================================================
# OPTION 5: Mixed — explicit domains + subdomain regex
# The two parameters are combined with OR logic by FastAPI:
# a request passes if it matches allow_origins OR allow_origin_regex.
# =====================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://myapp.com",                  # apex domain (regex above won't catch this)
        "https://partner.externalsite.com",   # external partner, not on your subdomain
    ],
    allow_origin_regex=r"https://.*\.myapp\.com",   # all your own subdomains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# =====================================================================
# OPTION 6: Dev/staging/prod switch in one block
# =====================================================================
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

ORIGINS_BY_ENV = {
    "development": [
        "http://localhost:3000",      # React dev server
        "http://localhost:8080",      # Vue / other local tooling
        "http://127.0.0.1:3000",
    ],
    "staging": [
        "https://staging.myapp.com",
        "https://staging-admin.myapp.com",
    ],
    "production": [
        "https://myapp.com",
        "https://admin.myapp.com",
        "https://app.myapp.com",
    ],
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS_BY_ENV.get(ENVIRONMENT, []),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
