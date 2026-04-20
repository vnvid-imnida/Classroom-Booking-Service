# Stage 1: Build
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Установка зависимостей
RUN apk add --no-cache git

# Копирование go.mod и go.sum
COPY go.mod go.sum ./

# Загрузка зависимостей
RUN go mod download

# Копирование исходного кода
COPY . .

# Компиляция
RUN CGO_ENABLED=0 GOOS=linux go build -o notification-service .

# Stage 2: Runtime
FROM alpine:latest

WORKDIR /app

# Установка необходимых пакетов
RUN apk add --no-cache ca-certificates

# Копирование бинарника из builder
COPY --from=builder /app/notification-service .

# Expose port
EXPOSE 8084

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8084/health || exit 1

# Run
CMD ["./notification-service"]
