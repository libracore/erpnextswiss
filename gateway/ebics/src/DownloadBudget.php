<?php
declare(strict_types=1);

namespace KT\Banking;

use Closure;
use EbicsApi\Ebics\Contracts\HttpClientInterface;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Http\Response;
use RuntimeException;

final class DownloadBudget implements HttpClientInterface
{
    public const MAX_SEGMENTS = 64;
    public const MAX_RESPONSE_BYTES = 20971520;
    public const MAX_SECONDS = 120;
    private bool $active = false;
    private int $requests = 0;
    private int $bytes = 0;
    private float $deadline = 0;
    private readonly Closure $clock;

    public function __construct(private readonly HttpClientInterface $inner, private readonly string $endpoint, ?Closure $clock = null)
    {
        $this->clock = $clock ?? static fn(): float => hrtime(true) / 1e9;
    }

    public function begin(): void
    {
        if ($this->active) throw new RuntimeException('Download transport already active');
        $this->active = true;
        $this->requests = $this->bytes = 0;
        $this->deadline = ($this->clock)() + self::MAX_SECONDS;
    }

    public function end(): void
    {
        $this->active = false;
    }

    public function post(string $url, Request $request): Response
    {
        if (!$this->active || $url !== $this->endpoint) throw new RuntimeException('Download transport scope is inactive or mismatched');
        if (++$this->requests > self::MAX_SEGMENTS + 1 || ($this->clock)() >= $this->deadline) {
            throw new RuntimeException('Download request or time budget exhausted');
        }
        $response = $this->inner->post($url, $request);
        $this->bytes += strlen($response->getContent());
        if ($this->bytes > self::MAX_RESPONSE_BYTES || ($this->clock)() >= $this->deadline) {
            throw new RuntimeException('Download response or time budget exhausted');
        }
        // Admission only, never authentication: the SDK still verifies signatures.
        foreach ($response->getElementsByTagNameNS('*', 'NumSegments') as $count) {
            $value = trim($count->textContent);
            if (!preg_match('/\A[0-9]{1,10}\z/', $value) || (int)$value > self::MAX_SEGMENTS) {
                throw new RuntimeException('Bank segment count exceeds download limit');
            }
        }
        return $response;
    }
}
