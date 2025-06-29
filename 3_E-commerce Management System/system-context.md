# System Context: AI-Powered E-Commerce Microservices System

## 1. Microservices
- **ProductService**: Manages product catalog, categories, pricing, and product search.
- **CustomerService**: Handles customer profiles, authentication, and account management.
- **OrderService**: Manages order placement, payment processing, and order tracking.
- **InventoryService**: Tracks stock levels, updates inventory, and manages stock reservations.
- **NotificationService**: Sends real-time and asynchronous notifications (email, SMS, in-app, SignalR).

## 2. Communication Patterns
- **REST**: Synchronous communication between services and with clients (e.g., placing orders, querying products).
- **Redis Streams**: Asynchronous event-driven communication for workflows (e.g., order placed → inventory update → notification).
- **SignalR**: Real-time updates to clients (e.g., live stock changes, order status updates).

## 3. Technology Stack
- **Backend Framework**: ASP.NET Core Web API (Clean Architecture, .NET 8)
- **ORM & Database**: Entity Framework Core with SQL Server (each service owns its DB)
- **Caching & Events**: Redis for distributed caching and Redis Streams for event-driven messaging
- **Real-Time**: SignalR for live updates to web/mobile clients
- **Testing**: xUnit for unit/integration tests, TestContainers for ephemeral test environments

## 4. Development Standards & Practices
- **Validation**: FluentValidation for input and business rule validation
- **Mapping**: AutoMapper for DTO/entity mapping
- **Logging**: Serilog for structured, centralized logging
- **Authentication**: JWT Bearer Authentication for secure, stateless APIs

## 5. High-Level Flow Example
- A customer places an order via the OrderService (REST API).
- OrderService emits an event to Redis Streams ("OrderPlaced").
- InventoryService consumes the event, updates stock, and emits an "InventoryChanged" event.
- NotificationService listens for both events and sends real-time updates via SignalR and/or email/SMS.

## 6. Deployment & Scalability
- Each microservice is containerized (Docker) and orchestrated (Docker Compose/Kubernetes).
- Services are independently deployable and scalable.
- Redis and SQL Server are shared infrastructure components, but each service has its own schema/database.
