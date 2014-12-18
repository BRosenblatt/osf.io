import hashlib

ADDRESS = '127.0.0.1'
PORT = 7777
DEBUG = True

CHUNK_SIZE = 65536  # 64KB

IDENTITY_METHOD = 'rest'
IDENTITY_API_URL = 'changeme'

FILE_PATH_PENDING = '/tmp/pending'
FILE_PATH_COMPLETE = '/tmp/complete'

BROKER_URL = 'amqp://'
CELERY_RESULT_BACKEND = 'redis://'
CELERY_IMPORTS = (
    'waterbutler.tasks.parity',
    'waterbutler.tasks.backup',
)
CELERY_DISABLE_RATE_LIMITS = True
CELERY_TASK_RESULT_EXPIRES = 60
# CELERY_ALWAYS_EAGER = True

# Parity options
PARITY_CONTAINER_NAME = None
PARITY_REDUNDANCY = 5

# Retry options
UPLOAD_RETRY_ATTEMPTS = 1
UPLOAD_RETRY_INIT_DELAY = 30
UPLOAD_RETRY_MAX_DELAY = 60 * 60
UPLOAD_RETRY_BACKOFF = 2
UPLOAD_RETRY_WARN_IDX = 5

HOOK_RETRY_ATTEMPTS = 1
HOOK_RETRY_INIT_DELAY = 30
HOOK_RETRY_MAX_DELAY = 60 * 60
HOOK_RETRY_BACKOFF = 2
HOOK_RETRY_WARN_IDX = None

PARITY_RETRY_ATTEMPTS = 1
PARITY_RETRY_INIT_DELAY = 30
PARITY_RETRY_MAX_DELAY = 60 * 60
PARITY_RETRY_BACKOFF = 2
PARITY_RETRY_WARN_IDX = None


PARITY_PROVIDER_NAME = 'cloudfiles'
PARITY_PROVIDER_CREDENTIALS = {}
PARITY_PROVIDER_SETTINGS = {}

AWS_ACCESS_KEY = 'changeme'
AWS_SECRET_KEY = 'changeme'
GLACIER_VAULT = 'changeme'

HMAC_SECRET = b'changeme'
HMAC_ALGORITHM = hashlib.sha256
