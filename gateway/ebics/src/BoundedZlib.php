<?php
declare(strict_types=1);

namespace KT\Banking;

use EbicsApi\Ebics\Contracts\Processor\ZipCompressorInterface;
use EbicsApi\Ebics\Services\Processor\ZipCompressor;
use RuntimeException;

final class BoundedZlib implements ZipCompressorInterface
{
    public const MAX_COMPRESSED_BYTES = 10485760;

    public function compress(string $data): string
    {
        return (new ZipCompressor())->compress($data);
    }

    public function uncompress(string $data): string
    {
        if (strlen($data) < 2 || strlen($data) > self::MAX_COMPRESSED_BYTES) {
            throw new RuntimeException('Invalid compressed payload size');
        }
        // Limit native zlib allocation before the SDK's persistence/receipt phase.
        // This unwraps EBICS zlib only; the inner ZIP remains an opaque original.
        $result = @gzuncompress($data, TransferJournal::MAX_BYTES);
        // PHP 8.5 may finish within its last growth buffer beyond max_length.
        if ($result === false || strlen($result) > TransferJournal::MAX_BYTES) {
            throw new RuntimeException('Invalid or oversized zlib payload');
        }
        return $result;
    }
}
