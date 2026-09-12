<?php
declare(strict_types=1);

namespace KT\Banking;

use DateTimeImmutable;
use DateTimeZone;
use InvalidArgumentException;

final readonly class ReadRequest
{
    public function __construct(
        public string $site,
        public string $connection,
        public string $participant,
        public string $request,
        public string $profile,
        public string $from,
        public string $until,
    ) {
        foreach ([$site, $connection, $participant, $request] as $value) {
            if (!preg_match('/\A[a-zA-Z0-9_-]{1,100}\z/', $value)) {
                throw new InvalidArgumentException('Opaque configured identities required');
            }
        }
        if (!in_array($profile, ['camt.053.001.08', 'camt.054.001.08'], true)) {
            throw new InvalidArgumentException('Only release-1 read profiles are allowed');
        }
        $start = self::date($from);
        $end = self::date($until);
        if ($end < $start || (int)$start->diff($end)->days > 31) {
            throw new InvalidArgumentException('Date window must be ordered and at most 32 inclusive days');
        }
    }

    public static function date(string $value): DateTimeImmutable
    {
        $date = DateTimeImmutable::createFromFormat('!Y-m-d', $value, new DateTimeZone('UTC'));
        if (!$date || $date->format('Y-m-d') !== $value) {
            throw new InvalidArgumentException('Exact calendar date required');
        }
        return $date;
    }

    public function key(): string
    {
        return hash('sha256', json_encode([$this->site, $this->connection, $this->request], JSON_THROW_ON_ERROR));
    }

    public function binding(): string
    {
        return json_encode(get_object_vars($this), JSON_THROW_ON_ERROR);
    }
}
