"""Constants for QR Login."""

DOMAIN = "qr_login"

# Options (configurable via the options flow)
CONF_CODE_TTL = "code_ttl"                # seconds a pending code lives
CONF_CROSS_USER = "allow_cross_user"      # admins may mint for another user
CONF_ALLOWED_USERS = "allowed_users"      # non-admin user IDs explicitly permitted to approve (self only)

DEFAULT_CODE_TTL = 120                    # 2 minutes — 1 min proved too rushed in real use
DEFAULT_CROSS_USER = True
DEFAULT_ALLOWED_USERS: list[str] = []

# Session lifecycle states
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_DENIED = "denied"

EVENT_APPROVED = "qr_login_approved"

CAR_PAGE_PATH = "/qr-login"
APPROVE_PANEL_PATH = "qr-approve"
API_BASE = "/api/qr_login"
