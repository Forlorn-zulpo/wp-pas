import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    READONLY = "readonly"


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class AssetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ImportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class SitePlatform(str, enum.Enum):
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    WORDPRESS = "wordpress"
    GENERIC = "generic"


class SiteStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SiteProductStatus(str, enum.Enum):
    BOUND = "bound"  # linked, never published
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    FAILED = "failed"


class CollectionMethod(str, enum.Enum):
    API = "api"
    HTTP_STATIC = "http_static"  # requests/BeautifulSoup/Scrapy
    BROWSER = "browser"  # Playwright, only when genuinely needed
    MANUAL = "manual"  # manually uploaded/entered, no live collection


class SupplierStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CollectionJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class AIProviderType(str, enum.Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    OPENAI_COMPATIBLE = "openai_compatible"  # local models / other vendors


class AITaskType(str, enum.Enum):
    PRODUCT_RECOGNITION = "product_recognition"
    TITLE_GENERATION = "title_generation"
    DESCRIPTION_GENERATION = "description_generation"
    ATTRIBUTE_EXTRACTION = "attribute_extraction"
    CATEGORY_SUGGESTION = "category_suggestion"
    IMAGE_ANALYSIS = "image_analysis"
    IMAGE_GENERATION = "image_generation"
    TRANSLATION = "translation"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PublicationJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"  # every item succeeded
    PARTIAL = "partial"  # some items succeeded, some failed
    FAILED = "failed"  # every item failed


class PublicationItemStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ARCHIVE = "archive"
    BULK_UPDATE = "bulk_update"
    IMPORT = "import"
    LOGIN = "login"
    BIND = "bind"
    UNBIND = "unbind"
    TEST_CONNECTION = "test_connection"
    PUBLISH = "publish"
    APPROVE = "approve"
    REJECT = "reject"
