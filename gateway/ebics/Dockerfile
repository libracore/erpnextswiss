FROM composer:2@sha256:d8f6343d3fae98107426bc49163ccad46ef85aabd4a27d80a74401fab4aba332 AS composer
FROM php:8.5-cli-alpine@sha256:aa66ee4275e0472bafcd18e35142499fcbda6ac90e641e751418e052e6a0d812 AS base
RUN apk add --no-cache libzip \
    && apk add --no-cache --virtual .build-deps $PHPIZE_DEPS libzip-dev \
    && docker-php-ext-install bcmath zip \
    && apk del .build-deps \
    && addgroup -g 10001 gateway && adduser -D -u 10001 -G gateway gateway
COPY --from=composer /usr/bin/composer /usr/local/bin/composer

FROM base AS lockfile-tooling
RUN apk add --no-cache git
WORKDIR /app

FROM lockfile-tooling AS dependencies
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-plugins --no-scripts --prefer-dist --no-interaction --classmap-authoritative
COPY src ./src
RUN composer dump-autoload --no-dev --no-plugins --no-scripts --classmap-authoritative
RUN rm -rf /app/vendor/ebics-api/ebics-client-php/.git

FROM base AS runtime
WORKDIR /app
COPY --from=dependencies /app /app
USER 10001:10001
CMD ["php", "-r", "fwrite(STDERR, 'Transport foundation only; no bank endpoint is configured.'); exit(2);"]

FROM runtime AS test
COPY tests ./tests
CMD ["php", "-d", "memory_limit=128M", "tests/run.php"]
