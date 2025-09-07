Below is a detailed **System Analysis and Requirements Gathering** document tailored for your **Car Detailing System**, based on the provided `models.py`, `admin.py`, `unfold_admin.py`, `base.py`, `dev.py`, `prod.py`, and the newly created API files (`serializers.py`, `views.py`, `urls.py`, `permissions.py`). This document outlines the system’s purpose, functional and non-functional requirements, stakeholders, system scope, and technical analysis to guide development and implementation.

---

# System Analysis and Requirements Gathering Document  
## Car Detailing System  

---

### 1. Introduction

#### 1.1 Purpose
The **Car Detailing System** is a web-based platform designed to facilitate car detailing services by connecting customers with dealers (service providers). The system supports booking management, payment processing, dealer verification, and external website integration via webhooks. It provides an admin interface for managing users, services, financials, and system operations, along with a RESTful API for programmatic access. This document captures the system’s requirements, stakeholders, and technical analysis to ensure alignment with business goals.

#### 1.2 Scope
The system includes:
- User management for customers and dealers.
- Service and booking management, including external bookings.
- Payment processing via Stripe (app-based and virtual cards for cash payments).
- Dealer financial tracking with variable commission rates.
- Webhook integration for dealers with external websites.
- Admin interface for system oversight and analytics.
- RESTful API for customer and dealer interactions, with proper authentication and permissions.
- Support for promotions, notifications, reviews, and dealer verification.

The system does not cover:
- Direct vehicle diagnostics or IoT integration.
- Customer-facing mobile app development (though APIs support future apps).
- Non-car detailing services (e.g., repairs, towing).

#### 1.3 Stakeholders
- **Customers**: Book detailing services, manage vehicles, and submit reviews.
- **Dealers**: Offer services, manage bookings, process payments, and integrate with external websites.
- **Admins**: Oversee system operations, approve dealers, manage financials, and monitor webhooks.
- **Developers**: Maintain and extend the system, integrate APIs, and ensure security.

---

### 2. System Analysis

#### 2.1 Current System Context
The Car Detailing System is a Django-based web application with a PostgreSQL (or SQLite in development) database, using Django REST Framework (DRF) for API endpoints. It leverages Django Unfold for a modern admin interface, Simple JWT for authentication, and WhiteNoise for static file serving in production. The system supports:
- User differentiation (customers, dealers, admins) via `UserProfile`.
- Booking sources (`app` and `external`) with variable commission rates.
- Stripe integration for payments and virtual cards for cash transactions.
- Webhook support for external dealer websites.
- A robust admin panel for managing all entities.

#### 2.2 Problem Statement
The car detailing industry lacks a streamlined platform to:
- Connect customers with verified dealers efficiently.
- Handle both app-based and external bookings with flexible payment options.
- Provide dealers with tools to manage services and financials transparently.
- Offer admins comprehensive oversight of operations, financials, and user verification.
- Ensure secure, scalable, and maintainable APIs for future expansion.

#### 2.3 Proposed Solution
The Car Detailing System addresses these issues by providing:
- A centralized platform for booking, payment, and service management.
- Role-based access control (RBAC) for customers, dealers, and admins.
- Automated commission calculations and financial tracking.
- Webhook integration for real-time updates to external dealer systems.
- A secure REST API with JWT authentication for programmatic access.
- A user-friendly admin interface with analytics and management tools.

---

### 3. Functional Requirements

#### 3.1 User Management
- **FR1.1**: Customers can register, update profiles (`CustomerProfile`), and manage vehicles (`Vehicle`).
- **FR1.2**: Dealers can register, submit verification documents (`DealerVerificationDocument`), and manage profiles (`DealerProfile`) with banking details.
- **FR1.3**: Admins can approve/reject dealer profiles and verification documents.
- **FR1.4**: System automatically creates `CustomerProfile` or `DealerProfile` on user registration via signals.

#### 3.2 Service Management
- **FR2.1**: Dealers can create, update, and deactivate services (`Service`) and categories (`ServiceCategory`).
- **FR2.2**: Dealers can define service availability (`ServiceAvailability`) by time and location (e.g., mobile or shop-based).
- **FR2.3**: Dealers can manage service slots (`ServiceSlot`) with availability status.
- **FR2.4**: External services and slots can be synced via `external_service_id` and `external_slot_id`.

#### 3.3 Booking Management
- **FR3.1**: Customers can book services (`Booking`) via the app or external dealer websites.
- **FR3.2**: Bookings support `app` and `external` sources, with `external_booking_id` for tracking.
- **FR3.3**: System calculates platform commissions (`platform_commission`, `dealer_amount`) based on `DealerProfile.commission_percentage` for app bookings; no commission for external bookings.
- **FR3.4**: Bookings can include promotions (`Promotion`) for discounts.
- **FR3.5**: Dealers can accept, reject, or cancel bookings, with deadlines (`dealer_response_deadline`).

#### 3.4 Payment Processing
- **FR4.1**: App bookings use Stripe for payments, recorded in `Payment` with `transaction_id` and `payment_method='customer_card'`.
- **FR4.2**: Dealers can process cash payments via virtual cards (`VirtualCard`), recorded in `Payment` with `payment_method='virtual_card'`.
- **FR4.3**: External bookings have no payment record or use `payment_method='external'`.
- **FR4.4**: Dealers can request payouts (`PayoutRequest`), updating `DealerProfile.current_balance`.
- **FR4.5**: `BalanceTransaction` logs all balance changes (bookings, payouts, adjustments).

#### 3.5 Webhook Integration
- **FR5.1**: Dealers with external websites can configure webhooks (`WebhookConfiguration`) for events (e.g., `booking.created`, `service.updated`).
- **FR5.2**: Webhook events (`WebhookEvent`) are logged (`WebhookLog`) with retry mechanisms.
- **FR5.3**: Webhooks support secure delivery with `secret_key`.

#### 3.6 Notifications and Reviews
- **FR6.1**: System sends notifications (`Notification`) to users via email, SMS, or both.
- **FR6.2**: Customers can submit reviews (`Review`) for completed bookings, updating `DealerProfile.rating`.
- **FR6.3**: Admins can monitor and moderate reviews.

#### 3.7 API Endpoints
- **FR7.1**: RESTful API endpoints for all models (`CustomerProfile`, `DealerProfile`, `Vehicle`, etc.) using DRF.
- **FR7.2**: Endpoints support CRUD operations with pagination (`PAGE_SIZE=20`).
- **FR7.3**: Authentication via Simple JWT (`Bearer` tokens).
- **FR7.4**: Permissions restrict access:
  - Admins: Full access to all endpoints.
  - Dealers: Manage own services, slots, bookings, webhooks, payouts, virtual cards, balance transactions, commission history, and verification documents.
  - Customers: Manage own profiles, vehicles, bookings, notifications, and reviews.
  - Read-only access for safe methods (GET) where applicable.

#### 3.8 Admin Interface
- **FR8.1**: Admin panel (Django Unfold) provides CRUD operations for all models.
- **FR8.2**: Custom list displays, filters, and search fields for efficient management.
- **FR8.3**: Inline editing for `DealerVerificationDocument` in `DealerProfile`.
- **FR8.4**: Sidebar navigation for all models, restricted to superusers.

---

### 4. Non-Functional Requirements

#### 4.1 Performance
- **NFR1.1**: API responses should return within 2 seconds under normal load (100 concurrent users).
- **NFR1.2**: Database queries optimized with indexes (e.g., `Booking.status`, `Payment.payment_method`).
- **NFR1.3**: Pagination limits API results to 20 items per page.

#### 4.2 Security
- **NFR2.1**: JWT authentication for all API endpoints.
- **NFR2.2**: Role-based permissions (`IsAdmin`, `IsDealer`, `IsCustomer`, `IsOwnerOrAdmin`).
- **NFR2.3**: HTTPS enforced in production (`SECURE_SSL_REDIRECT=True`).
- **NFR2.4**: Sensitive data (e.g., `VirtualCard.card_number`, `DealerProfile.webhook_secret`) encrypted or securely handled.
- **NFR2.5**: CSRF and XSS protection via Django middleware.
- **NFR2.6**: HSTS headers and secure cookies in production.

#### 4.3 Scalability
- **NFR3.1**: System supports up to 10,000 users (customers and dealers) and 100,000 bookings.
- **NFR3.2**: Redis caching for session management and frequent queries.
- **NFR3.3**: Database migrations handle schema changes without downtime.

#### 4.4 Usability
- **NFR4.1**: Admin interface is intuitive with collapsible fieldsets and autocomplete fields.
- **NFR4.2**: API responses include clear error messages and follow REST standards.
- **NFR4.3**: Documentation (via `drf_yasg`) for API endpoints.

#### 4.5 Reliability
- **NFR5.1**: System uptime of 99.9% in production.
- **NFR5.2**: Webhook retries (up to 3 attempts) for failed deliveries.
- **NFR5.3**: Logging (`django.log`) for debugging and auditing.

#### 4.6 Maintainability
- **NFR6.1**: Code follows Django best practices with modular apps (`Authentication`, `cardealing`, `api`).
- **NFR6.2**: Environment-specific settings (`base.py`, `dev.py`, `prod.py`) for flexibility.
- **NFR6.3**: Automated tests for models, views, and APIs (to be implemented).

---

### 5. System Architecture

#### 5.1 Components
- **Frontend**: Django Unfold admin interface for admins, future customer/dealer portals (not implemented).
- **Backend**: Django with DRF, handling business logic, API endpoints, and signals.
- **Database**: PostgreSQL (production) or SQLite (development), with models defined in `models.py`.
- **API**: RESTful endpoints (`api/urls.py`) with JWT authentication and custom permissions.
- **External Services**:
  - Stripe for payment processing and virtual cards.
  - SMTP (e.g., Gmail) for email notifications.
  - Redis for caching and session management.
- **Static/Media**: WhiteNoise for static files, `MEDIA_ROOT` for uploaded files (e.g., `DealerVerificationDocument.document_file`).

#### 5.2 Data Flow
1. **Customer Booking**:
   - Customer creates a booking via API (`POST /api/bookings/`).
   - Signal calculates `platform_commission` and `dealer_amount` based on `source` and `DealerProfile.commission_percentage`.
   - Payment processed via Stripe (`Payment`) or virtual card.
   - Webhook notifies dealer’s external website (`WebhookEvent`).
2. **Dealer Management**:
   - Dealer manages services, slots, and availability via API or admin panel.
   - Payouts requested via `PayoutRequest`, logged in `BalanceTransaction`.
3. **Admin Oversight**:
   - Admins monitor bookings, payments, and dealer verification via admin panel.
   - Review financials (`BalanceTransaction`, `CommissionHistory`) and moderate reviews.

#### 5.3 Deployment
- **Development**: `DEBUG=True`, SQLite, console email backend, Django Debug Toolbar.
- **Production**: `DEBUG=False`, PostgreSQL, Redis, WhiteNoise, SMTP email, secure headers (HSTS, XSS protection).
- **Environment Variables**: Managed via `django-environ` (e.g., `SECRET_KEY`, `DATABASE_URL`, `EMAIL_HOST`).

---

### 6. Technical Requirements

#### 6.1 Technology Stack
- **Framework**: Django 4.x, Django REST Framework
- **Authentication**: Simple JWT
- **Admin Interface**: Django Unfold
- **Database**: PostgreSQL (production), SQLite (development)
- **Caching**: Redis
- **Static Files**: WhiteNoise
- **Dependencies**: `django-environ`, `drf-yasg`, `corsheaders`, `debug_toolbar` (dev), `django_extensions` (dev)

#### 6.2 API Endpoints
| Endpoint | Model | Permissions | Description |
|----------|-------|-------------|-------------|
| `/api/customer-profiles/` | `CustomerProfile` | Customer, Admin | Manage customer profiles |
| `/api/dealer-profiles/` | `DealerProfile` | Dealer, Admin | Manage dealer profiles |
| `/api/vehicles/` | `Vehicle` | Owner, Admin | Manage vehicles |
| `/api/service-categories/` | `ServiceCategory` | Admin | Manage service categories |
| `/api/services/` | `Service` | Dealer, Admin | Manage dealer services |
| `/api/service-availabilities/` | `ServiceAvailability` | Dealer, Admin | Manage service availability |
| `/api/service-slots/` | `ServiceSlot` | Dealer, Admin | Manage service slots |
| `/api/promotions/` | `Promotion` | Admin | Manage promotions |
| `/api/bookings/` | `Booking` | Customer, Dealer, Admin | Manage bookings |
| `/api/webhook-configurations/` | `WebhookConfiguration` | Dealer, Admin | Manage webhooks |
| `/api/webhook-events/` | `WebhookEvent` | Dealer, Admin | View webhook events |
| `/api/webhook-logs/` | `WebhookLog` | Admin | View webhook logs |
| `/api/payments/` | `Payment` | Admin | View payment records |
| `/api/payout-requests/` | `PayoutRequest` | Dealer, Admin | Manage payout requests |
| `/api/virtual-cards/` | `VirtualCard` | Dealer, Admin | Manage virtual cards |
| `/api/balance-transactions/` | `BalanceTransaction` | Dealer, Admin | View balance transactions |
| `/api/notifications/` | `Notification` | Authenticated | View user notifications |
| `/api/reviews/` | `Review` | Customer, Dealer, Admin | Manage reviews |
| `/api/dealer-verification-documents/` | `DealerVerificationDocument` | Dealer, Admin | Manage verification documents |
| `/api/commission-history/` | `CommissionHistory` | Dealer, Admin | View commission history |

#### 6.3 Database Schema
- **Models**: Defined in `models.py` with relationships (e.g., `Booking` links to `Customer`, `ServiceSlot`, `Vehicle`, `Promotion`).
- **Indexes**: Applied to frequently queried fields (e.g., `Booking.status`, `Payment.payment_method`).
- **Signals**: Automate profile creation (`CustomerProfile`, `DealerProfile`) and booking financials (`platform_commission`, `dealer_amount`).

---

### 7. Constraints and Assumptions

#### 7.1 Constraints
- **C1**: System assumes dealers have valid Stripe accounts for payments and virtual cards.
- **C2**: External websites must support webhook endpoints with HTTPS.
- **C3**: Admin access restricted to superusers; additional roles require custom permissions.
- **C4**: Currency fixed to BDT (`Payment.currency='BDT'`).

#### 7.2 Assumptions
- **A1**: Customers and dealers have access to modern browsers or API clients.
- **A2**: Email/SMS gateways are configured for notifications.
- **A3**: Stripe API keys and Redis URL are provided via environment variables.
- **A4**: Future mobile apps will use the provided APIs.

---

### 8. Risks and Mitigation
- **R1**: Data breaches of sensitive information (e.g., bank details, virtual cards).
  - **Mitigation**: Use HTTPS, encrypt sensitive fields, and follow OWASP security practices.
- **R2**: Webhook delivery failures to external websites.
  - **Mitigation**: Implement retry logic (up to 3 attempts) and log failures (`WebhookLog`).
- **R3**: Scalability issues with high booking volumes.
  - **Mitigation**: Use Redis caching, optimize queries with indexes, and monitor performance.
- **R4**: Incorrect commission calculations.
  - **Mitigation**: Log commission changes (`CommissionHistory`) and test signal logic thoroughly.

---

### 9. Next Steps
1. **Implementation**:
   - Deploy API endpoints and test with Postman or Swagger (`drf_yasg`).
   - Integrate Stripe for payment and virtual card processing.
   - Configure email/SMS notifications.
2. **Testing**:
   - Write unit tests for models, views, and signals.
   - Test API permissions for all user roles.
   - Simulate high load to verify performance.
3. **Documentation**:
   - Generate API documentation using `drf_yasg`.
   - Document admin workflows and dealer webhook setup.
4. **Deployment**:
   - Configure production environment (`prod.py`) with PostgreSQL and Redis.
   - Run migrations and collect static files.
5. **Future Enhancements**:
   - Add customer/dealer portals using frontend frameworks (e.g., React).
   - Implement analytics dashboard for admins.
   - Support multi-currency payments.

---

### 10. Conclusion
The Car Detailing System provides a robust platform for managing car detailing services, with flexible booking, payment, and webhook capabilities. The RESTful API, secure authentication, and comprehensive admin interface meet the needs of customers, dealers, and admins. By addressing the outlined requirements and mitigating risks, the system ensures scalability, security, and usability for all stakeholders.

---

If you need specific sections expanded (e.g., detailed API workflows, test cases, or deployment guides), or if you want to add features (e.g., analytics endpoints, custom admin views), let me know!